import uuid
from flask import Flask, request, jsonify
from rag import agentic_rag
import db

app = Flask(__name__)

@app.route("/question", methods=["POST"])
def handle_question():
    data = request.json
    question = data["question"]

    if not question:
        return jsonify({"error": "No question provided"}), 400

    conversation_id = str(uuid.uuid4())
    answer_data = agentic_rag(question)

    db.save_conversation( 
        conversation_id=conversation_id, 
        question=question,
        answer_data=answer_data
    )
  
    result = {
        "conversation_id": conversation_id,
        "question": question,
        "answer": answer_data["answer"],
    }

    return jsonify(result)

@app.route("/feedback", methods=["POST"])
def handle_feedback():
    data = request.json
    conversation_id = data["conversation_id"]
    feedback = data["feedback"]

    if not conversation_id or feedback not in [1, -1]:
        return jsonify({"error": "Invalid input"}), 400

    db.save_feedback(
        conversation_id=conversation_id,
        feedback=feedback,
    )

    return jsonify({"message": f"Feedback received: {feedback}"})

if __name__ == "__main__":
    print("Starting Flask...")
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=5000)

