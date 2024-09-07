from flask import Flask, jsonify, request, render_template
import pandas as pd
import random
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pymongo import MongoClient

app = Flask(__name__)

# load files===========================================================================================================
trending_products = pd.read_csv("models/trending_products.csv")
train_data = pd.read_csv("models/clean_data.csv")

# database configuration---------------------------------------
# app.secret_key = "alskdjfwoeieiurlskdjfslkdjf"
# app.config['SQLALCHEMY_DATABASE_URI'] = "mysql://root:@localhost/ecom"
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db = SQLAlchemy(app)

# Connect to MongoDB running on localhost at port 27017 (default port)
client = MongoClient('mongodb://localhost:27017/')
# Select a database (it will create a new one if it doesn't exist)
db = client['dss']

# Select a collection (like a table in relational databases)
collection = db['collections']
user_collection = db['users']




# Recommendations functions============================================================================================
# Function to truncate product name
def truncate(text, length):
    if len(text) > length:
        return text[:length] + "..."
    else:
        return text


def content_based_recommendations(train_data, item_name, top_n=10):
    # Check if the item name exists in the training data
    if item_name not in train_data['Name'].values:
        print(f"Item '{item_name}' not found in the training data.")
        return pd.DataFrame()

    # Create a TF-IDF vectorizer for item descriptions
    tfidf_vectorizer = TfidfVectorizer(stop_words='english')

    # Apply TF-IDF vectorization to item descriptions
    tfidf_matrix_content = tfidf_vectorizer.fit_transform(train_data['Tags'])

    # Calculate cosine similarity between items based on descriptions
    cosine_similarities_content = cosine_similarity(tfidf_matrix_content, tfidf_matrix_content)

    # Find the index of the item
    item_index = train_data[train_data['Name'] == item_name].index[0]

    # Get the cosine similarity scores for the item
    similar_items = list(enumerate(cosine_similarities_content[item_index]))

    # Sort similar items by similarity score in descending order
    similar_items = sorted(similar_items, key=lambda x: x[1], reverse=True)

    # Get the top N most similar items (excluding the item itself)
    top_similar_items = similar_items[1:top_n+1]

    # Get the indices of the top similar items
    recommended_item_indices = [x[0] for x in top_similar_items]

    # Get the details of the top similar items
    recommended_items_details = train_data.iloc[recommended_item_indices][['Name', 'ReviewCount', 'Brand', 'ImageURL', 'Rating']]

    return recommended_items_details
# routes===============================================================================



@app.route("/signup", methods=['POST',])
def signup():
    if request.is_json:
        data = request.get_json()
        
        # Extract the required fields
        topic = data.get('topic')
        level = data.get('level')
        learning_preference = data.get('learning_preference')
        learning_goal = data.get('learning_goal')

        # Create a new user document
        new_user = {
            'userId': str(result.inserted_id),
            'title': topic,
            'level_of_difficulty': level,
            'learning_style': learning_preference,
            'learning_goals': learning_goal,
        }

        try:
            # Insert the document into the collection
            result = user_collection.insert_one(new_user)

            # Return the inserted document ID
            return jsonify({"message": "User created", "user_id": str(result.inserted_id)}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "Request must be JSON"}), 400
    
    
@app.route('/home', methods=['GET'])
def search_users():
    # Get the title from the query parameters
    title = request.args.get('title', '')
    
    # Define the MongoDB collection
    collection = user_collection
    
    # Find users matching the title in the tags
    users = collection.find({
        'tags': {'$regex': title, '$options': 'i'}
    })
    
    # Convert the MongoDB cursor to a list of dictionaries
    users_list = list(users)
    
    # Sort users based on rating
    sorted_users = sorted(users_list, key=lambda x: x.get('rating', 0), reverse=True)
    
    # Return the sorted list as JSON
    return jsonify(sorted_users[:10])


@app.route('/add_activity', methods=['POST'])
def add_activity():
    # Get JSON data from request
    data = request.json
    
    # Check if the required fields are in the request
    required_fields = [
        'userId', 'id', 'previous_test_scores', 'learning_style', 
        'learning_goals', 'course_duration', 'engagement_time_spent',
        'module_objectives', 'assessment_scores', 'feedback_comments', 
        'feedback_ratings', 'level_of_difficulty'
    ]
    
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing field: {field}'}), 400
    
    # Define the MongoDB collection
    collection = db['activity']
    
    # Query for matching userId and id
    query = {
        'userId': {'$in': data['userId']},
        'id': {'$in': data['id']}
    }
    
    # Data to update or insert
    update_data = {
        '$set': {
            'previous_test_scores': data['previous_test_scores'],
            'learning_style': data['learning_style'],
            'learning_goals': data['learning_goals'],
            'course_duration': data['course_duration'],
            'engagement_time_spent': data['engagement_time_spent'],
            'module_objectives': data['module_objectives'],
            'assessment_scores': data['assessment_scores'],
            'feedback_comments': data['feedback_comments'],
            'feedback_ratings': data['feedback_ratings'],
            'level_of_difficulty': data['level_of_difficulty']
        }
    }
    
    # Update or insert the data
    result = collection.update_one(query, update_data, upsert=True)
    
    if result.matched_count > 0:
        message = 'Data updated successfully'
    else:
        message = 'Data inserted successfully'
    
    return jsonify({'message': message})



if __name__=='__main__':
    app.run(debug=True)