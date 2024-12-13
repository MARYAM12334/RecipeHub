import os
import re
import math
from collections import defaultdict, Counter
from flask_cors import CORS, cross_origin
from flask import Flask, request, jsonify
import fitz  # PyMuPDF
from rapidfuzz import fuzz

########################################
# Configuration / Setup
########################################

PDF_DIR = "pdfs"  # Your directory with PDFs in category subfolders
stopwords = set(["the", "and", "of", "in", "to", "a"])


########################################
# PDF Text & Title Extraction
########################################

def extract_text_and_title(pdf_path):
    """
    Extract text and derive a title from the PDF using PyMuPDF (fitz).
    Title Heuristic:
    1. On the first page, extract text blocks with their font sizes.
    2. Choose the line with the largest font size as the title.
    3. If no textual blocks or tie, fallback to first line or filename.
    """
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text("text")

    # Attempt to find the largest font line on the first page
    title = None
    if len(doc) > 0:
        page = doc[0]
        # Extract text with details
        blocks = page.get_text("dict")["blocks"]
        candidate_lines = []
        for b in blocks:
            if "lines" in b:
                for l in b["lines"]:
                    line_str = "".join([s["text"] for s in l["spans"]]).strip()
                    # Compute average font size for the line
                    if len(l["spans"]) > 0:
                        avg_font_size = sum([s["size"] for s in l["spans"]]) / len(l["spans"])
                        candidate_lines.append((line_str, avg_font_size))

        if candidate_lines:
            # Pick line with largest font size
            candidate_lines.sort(key=lambda x: x[1], reverse=True)
            title_candidate = candidate_lines[0][0].strip()
            # If title candidate is empty or too generic, fallback
            if title_candidate:
                title = title_candidate

    # If no title found by font size heuristic, try the first line of text
    if not title:
        lines = [l.strip() for l in full_text.split('\n') if l.strip()]
        if lines:
            title = lines[0]
        else:
            # Fallback to filename
            filename = os.path.basename(pdf_path)
            title = os.path.splitext(filename)[0].replace('_', ' ')

    doc.close()
    return title, full_text


########################################
# Tokenization & Inverted Index
########################################

def tokenize(text):
    tokens = re.findall(r"\w+", text.lower())
    return [t for t in tokens if t not in stopwords]


def build_inverted_index(pdf_dir):
    doc_id = 0
    documents = {}
    inverted_index = defaultdict(lambda: defaultdict(int))

    for root, dirs, files in os.walk(pdf_dir):
        # Determine category
        if root == pdf_dir:
            current_category = "Uncategorized"
        else:
            current_category = os.path.basename(root)

        for f in files:
            if f.lower().endswith(".pdf"):
                pdf_path = os.path.join(root, f)
                title, full_text = extract_text_and_title(pdf_path)

                doc_id += 1
                documents[doc_id] = {
                    "title": title,
                    "category": current_category,
                    "path": pdf_path,
                    "text": full_text
                }

                tokens = tokenize(full_text)
                tf_counts = Counter(tokens)
                for token, count in tf_counts.items():
                    inverted_index[token][doc_id] = count

    N = len(documents)
    idf = {}
    for token, doc_dict in inverted_index.items():
        df = len(doc_dict)
        idf[token] = math.log((N / df), 10) if df else 0.0

    return documents, inverted_index, idf

########################################
# Search Functions
########################################

def tf_idf_score(tf, idf):
    return (1 + math.log(tf, 10)) * idf if tf > 0 else 0


def general_search(query_tokens, documents, inverted_index, idf):
    scores = defaultdict(float)
    for token in query_tokens:
        if token in inverted_index:
            for doc_id, tf in inverted_index[token].items():
                scores[doc_id] += tf_idf_score(tf, idf[token])
    results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return results

def search_by_phrase(phrase, documents):
    results = []
    for doc_id, doc in documents.items():
        if phrase.lower() in doc["text"].lower():
            results.append((doc_id, len(phrase)))  # Length of phrase as relevance score
    # Sort by relevance (arbitrary score for now)
    results.sort(key=lambda x: x[1], reverse=True)
    return results

def search_by_category(query_tokens, category, documents, inverted_index, idf):
    category = category.strip().lower()

    # If category is empty, behave like a general search (no category filtering)
    if category == "":
        return general_search(query_tokens, documents, inverted_index, idf)

    category_docs = [
        doc_id for doc_id, doc in documents.items()
        if doc["category"].strip().lower() == category
    ]

    category_docs_set = set(category_docs)
    scores = defaultdict(float)

    for token in query_tokens:
        if token in inverted_index:
            for doc_id, tf in inverted_index[token].items():
                if doc_id in category_docs_set:
                    scores[doc_id] += tf_idf_score(tf, idf[token])

    results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return results

def search_by_title(query, documents):
    results = []
    for doc_id, doc in documents.items():
        title = doc["title"].lower()
        ratio = fuzz.partial_ratio(query.lower(), title)
        if ratio > 60:
            results.append((doc_id, ratio))
    results.sort(key=lambda x: x[1], reverse=True)
    return results


########################################
# Fuzzy Search (Content) Example
########################################

def fuzzy_search(query, documents, inverted_index, idf):
    # Do an initial retrieval using TF-IDF
    query_tokens = tokenize(query)
    initial_results = general_search(query_tokens, documents, inverted_index, idf)
    top_results = initial_results[:20]  # Arbitrarily pick top 20
    # Re-rank by fuzzy match on doc text+title
    reranked = []
    for doc_id, _ in top_results:
        text_block = documents[doc_id]["title"] + " " + documents[doc_id]["text"]
        ratio = fuzz.token_set_ratio(query.lower(), text_block.lower())
        reranked.append((doc_id, ratio))
    reranked.sort(key=lambda x: x[1], reverse=True)
    return reranked


def sort_results(results, documents, sort_by="relevance", ascending=False):
    """
    Sort the search results based on the specified criteria.

    Args:
        results: List of tuples (doc_id, score).
        documents: Dictionary containing document metadata.
        sort_by: Sorting criteria - "relevance", "title", "category", "length".
        ascending: Boolean to determine sort order.

    Returns:
        Sorted list of results.
    """
    if sort_by == "relevance":
        # Sort by score (default behavior)
        sorted_results = sorted(results, key=lambda x: x[1], reverse=not ascending)
    elif sort_by == "title":
        # Sort by title (alphabetical)
        sorted_results = sorted(
            results,
            key=lambda x: documents[x[0]]["title"].lower(),
            reverse=not ascending
        )
    elif sort_by == "category":
        # Sort by category
        sorted_results = sorted(
            results,
            key=lambda x: documents[x[0]]["category"].lower(),
            reverse=not ascending
        )
    elif sort_by == "length":
        # Sort by document length (number of characters in the text)
        sorted_results = sorted(
            results,
            key=lambda x: len(documents[x[0]]["text"]),
            reverse=not ascending
        )
    else:
        # Default to relevance if invalid sort_by is provided
        sorted_results = sorted(results, key=lambda x: x[1], reverse=not ascending)

    return sorted_results


########################################
# Flask App / API
########################################

app = Flask(__name__)

documents, inverted_index, idf = build_inverted_index(PDF_DIR)


@app.route("/search", methods=["GET"])
@cross_origin()

def api_search():
    query = request.args.get("query", "")
    sort_by = request.args.get("sort_by", "relevance")  # Default to relevance
    ascending = request.args.get("ascending", "false").lower() == "true"  # Default to descending

    query_tokens = tokenize(query)
    results = general_search(query_tokens, documents, inverted_index, idf)
    sorted_results = sort_results(results, documents, sort_by=sort_by, ascending=ascending)

    response = [{
        "doc_id": doc_id,
        "score": score,
        "title": documents[doc_id]["title"],
        "category": documents[doc_id]["category"],
        "path": documents[doc_id]["path"]
    } for doc_id, score in sorted_results]
    return jsonify(response)

@app.route("/search/by_category", methods=["GET"])
@cross_origin()

def api_search_category():
    query = request.args.get("query", "")
    category = request.args.get("category", "")
    sort_by = request.args.get("sort_by", "relevance")
    ascending = request.args.get("ascending", "false").lower() == "true"

    query_tokens = tokenize(query)
    results = search_by_category(query_tokens, category, documents, inverted_index, idf)
    sorted_results = sort_results(results, documents, sort_by=sort_by, ascending=ascending)

    response = [{
        "doc_id": doc_id,
        "score": score,
        "title": documents[doc_id]["title"],
        "category": documents[doc_id]["category"],
        "path": documents[doc_id]["path"]
    } for doc_id, score in sorted_results]
    return jsonify(response)

@app.route("/search/by_title", methods=["GET"])
@cross_origin()

def api_search_title():
    query = request.args.get("query", "")
    results = search_by_title(query, documents)
    response = [{
        "doc_id": doc_id,
        "score": score,
        "title": documents[doc_id]["title"],
        "category": documents[doc_id]["category"],
        "path": documents[doc_id]["path"]
    } for doc_id, score in results]
    return jsonify(response)


@app.route("/fuzzy_search", methods=["GET"])
@cross_origin()

def api_fuzzy_search():
    query = request.args.get("query", "")
    results = fuzzy_search(query, documents, inverted_index, idf)
    response = [{
        "doc_id": doc_id,
        "fuzzy_score": fuzzy_score,
        "title": documents[doc_id]["title"],
        "category": documents[doc_id]["category"],
        "path": documents[doc_id]["path"]
    } for doc_id, fuzzy_score in results]
    return jsonify(response)

@app.route("/search/by_phrase", methods=["GET"])
@cross_origin()

def api_search_by_phrase():
    phrase = request.args.get("phrase", "")
    results = search_by_phrase(phrase, documents)
    response = [{
        "doc_id": doc_id,
        "relevance_score": score,
        "title": documents[doc_id]["title"],
        "category": documents[doc_id]["category"],
        "path": documents[doc_id]["path"]
    } for doc_id, score in results]
    return jsonify(response)


def search_by_proximity(terms, max_distance, documents):
    results = []
    for doc_id, doc in documents.items():
        text = doc["text"].lower().split()
        positions = {term: [i for i, word in enumerate(text) if word == term] for term in terms}

        # Check proximity between term positions
        for i in range(len(terms) - 1):
            for p1 in positions[terms[i]]:
                for p2 in positions[terms[i + 1]]:
                    if abs(p1 - p2) <= max_distance:
                        results.append((doc_id, max_distance - abs(p1 - p2)))  # Higher score for closer matches
                        break
    results.sort(key=lambda x: x[1], reverse=True)
    return results
@app.route("/search/proximity", methods=["GET"])
@cross_origin()

def api_search_proximity():
    terms = request.args.get("terms", "").split(",")  # Comma-separated terms
    max_distance = int(request.args.get("max_distance", "5"))
    results = search_by_proximity(terms, max_distance, documents)
    response = [{
        "doc_id": doc_id,
        "score": score,
        "title": documents[doc_id]["title"],
        "category": documents[doc_id]["category"],
        "path": documents[doc_id]["path"]
    } for doc_id, score in results]
    return jsonify(response)
def boolean_search(query, inverted_index, documents):
    query = query.lower()
    tokens = re.split(r"\s+(and|or|not)\s+", query)  # Split by operators
    results = set()

    for i, token in enumerate(tokens):
        token = token.strip()
        if token in {"and", "or", "not"}:
            continue

        token_results = set(inverted_index[token].keys()) if token in inverted_index else set()
        if i > 0 and tokens[i - 1] == "not":
            results -= token_results
        elif i > 0 and tokens[i - 1] == "or":
            results |= token_results
        else:  # First token or "and"
            if not results:
                results = token_results
            else:
                results &= token_results

    # Convert results to list and compute arbitrary scores
    return [(doc_id, len(documents[doc_id]["text"])) for doc_id in results]
@app.route("/search/boolean", methods=["GET"])
@cross_origin()
def api_boolean_search():
    query = request.args.get("query", "")
    results = boolean_search(query, inverted_index, documents)
    response = [{
        "doc_id": doc_id,
        "score": score,
        "title": documents[doc_id]["title"],
        "category": documents[doc_id]["category"],
        "path": documents[doc_id]["path"]
    } for doc_id, score in results]
    return jsonify(response)

if __name__ == "__main__":
    app.run(port=1999, debug=True)
CORS(app, resources={r"/*": {"origins": "*"}})
