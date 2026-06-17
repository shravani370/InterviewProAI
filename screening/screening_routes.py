"""Screening routes blueprint for interview screening functionality"""
import time
import random
import logging
from flask import Blueprint, render_template, session, request, redirect, url_for, flash
from models.db import db, User, ScreeningResult
from utils.ai_engine import generate_question, generate_mcq_questions, generate_coding_questions
from functools import wraps

logger = logging.getLogger(__name__)

# Create Blueprint
screening_bp = Blueprint('screening', __name__, url_prefix='')

def login_required(f):
    """Decorator to require login for screening routes"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user'):
            return redirect('/google-login')
        return f(*args, **kwargs)
    return wrapper

@screening_bp.route('/mock', methods=['GET', 'POST'])
@login_required
def mock_interview():
    """Start a mock interview session"""
    
    # GET request - redirect to start interview
    if request.method == 'GET':
        return redirect(url_for('start'))
    
    # POST request - handle role selection
    role = request.form.get('role', '').strip()
    if not role:
        flash('❌ Please select a role', 'error')
        return redirect(url_for('start'))
    
    # Initialize interview session
    current_user = session.get('user')
    current_email = session.get('email')
    
    # Clear interview state while preserving auth
    session.clear()
    session['user'] = current_user
    session['email'] = current_email
    
    # Generate first question
    first_q = generate_question(role)
    
    # Initialize interview state
    session['topic'] = role
    session['mode'] = 'chat'
    session['question'] = first_q
    session['count'] = 0
    session['messages'] = [{'role': 'ai', 'text': first_q, 'type': 'question'}]
    session['asked_questions'] = [first_q]
    session['answers'] = []
    session['results'] = []
    session.modified = True
    
    return redirect(url_for('interview'))

# ═══════════════════════════════════════════════════════════════════════════════
# MCQ QUESTION POOLS — keyed by role keyword, 15+ Qs each so 10 are sampled
# ═══════════════════════════════════════════════════════════════════════════════

MCQ_POOLS = {

    "software engineer": [
        {"q": "What does SOLID stand for in software design?", "options": ["A set of 5 OOP principles", "A database design pattern", "A testing framework", "A deployment strategy"], "answer": 0},
        {"q": "Which data structure gives O(1) average lookup time?", "options": ["Array", "Linked List", "Hash Map", "Binary Tree"], "answer": 2},
        {"q": "What is the time complexity of QuickSort in the average case?", "options": ["O(n)", "O(n log n)", "O(n²)", "O(log n)"], "answer": 1},
        {"q": "What is a race condition?", "options": ["A CPU benchmark test", "When two threads access shared data simultaneously causing bugs", "A network latency issue", "A type of memory leak"], "answer": 1},
        {"q": "Which HTTP status code means 'Not Found'?", "options": ["200", "301", "403", "404"], "answer": 3},
        {"q": "What is the purpose of a mutex?", "options": ["To speed up threads", "To prevent simultaneous access to a shared resource", "To allocate memory", "To serialize data"], "answer": 1},
        {"q": "What does REST stand for?", "options": ["Remote Execution State Transfer", "Representational State Transfer", "Resource Endpoint Standard Transfer", "Reliable Execution and Storage Technology"], "answer": 1},
        {"q": "Which of the following is NOT a creational design pattern?", "options": ["Singleton", "Factory", "Observer", "Builder"], "answer": 2},
        {"q": "What is the purpose of an index in a database?", "options": ["To store backups", "To speed up query lookups", "To enforce foreign keys", "To encrypt data"], "answer": 1},
        {"q": "What is tail recursion?", "options": ["Recursion with no base case", "Recursion where the recursive call is the last operation", "Recursion using a stack", "Recursion that never terminates"], "answer": 1},
        {"q": "Which sorting algorithm is stable by default?", "options": ["Quick Sort", "Heap Sort", "Merge Sort", "Selection Sort"], "answer": 2},
        {"q": "What is the CAP theorem?", "options": ["Consistency, Availability, Partition tolerance — only 2 can be guaranteed", "A CPU architecture principle", "A caching strategy", "A cloud deployment model"], "answer": 0},
        {"q": "What does 'idempotent' mean in REST APIs?", "options": ["The request changes state every time", "Calling the endpoint multiple times has the same effect as once", "The response is always cached", "The API requires authentication"], "answer": 1},
        {"q": "What is a deadlock?", "options": ["A program that crashes on startup", "Two or more threads waiting on each other indefinitely", "A memory overflow error", "A failed network request"], "answer": 1},
        {"q": "What is the difference between a process and a thread?", "options": ["No difference", "A process has its own memory space; threads share memory", "Threads are slower than processes", "A process runs in user space only"], "answer": 1},
        {"q": "What is Big O notation used for?", "options": ["Measuring code readability", "Describing algorithm time and space complexity", "Counting lines of code", "Measuring test coverage"], "answer": 1},
        {"q": "What does DRY stand for in software engineering?", "options": ["Don't Repeat Yourself", "Do Run Yearly", "Data Retrieval Yield", "Dynamic Runtime YAML"], "answer": 0},
        {"q": "What is the purpose of unit testing?", "options": ["To test the entire application end-to-end", "To test individual functions or components in isolation", "To measure application performance", "To validate UI designs"], "answer": 1},
        {"q": "What is dependency injection?", "options": ["Importing libraries at runtime", "Providing dependencies to a class from outside rather than creating them internally", "A design pattern for singletons", "A testing framework feature"], "answer": 1},
        {"q": "What is Git rebase used for?", "options": ["Deleting branches", "Rewriting commit history by moving or combining commits onto a new base", "Merging two branches with a merge commit", "Reverting the last commit"], "answer": 1},
    ],

    "data analyst": [
        {"q": "Which SQL clause is used to filter grouped results?", "options": ["WHERE", "HAVING", "GROUP BY", "ORDER BY"], "answer": 1},
        {"q": "What does a box plot show?", "options": ["Correlation between two variables", "Distribution, median, quartiles and outliers", "Time series trends", "Frequency of categories"], "answer": 1},
        {"q": "Which of the following is a measure of central tendency?", "options": ["Variance", "Standard Deviation", "Median", "Range"], "answer": 2},
        {"q": "What is a pivot table used for?", "options": ["Sorting raw data", "Summarizing and aggregating data", "Creating charts", "Cleaning null values"], "answer": 1},
        {"q": "Which Python library is primarily used for data manipulation?", "options": ["NumPy", "Matplotlib", "Pandas", "Scikit-learn"], "answer": 2},
        {"q": "What does ETL stand for?", "options": ["Extract, Transfer, Load", "Extract, Transform, Load", "Export, Transfer, Link", "Encode, Test, Launch"], "answer": 1},
        {"q": "What is a null hypothesis?", "options": ["The hypothesis that is always true", "The default assumption that there is no effect or relationship", "The hypothesis with the highest probability", "The alternative hypothesis"], "answer": 1},
        {"q": "Which chart type is best for showing trends over time?", "options": ["Pie Chart", "Bar Chart", "Line Chart", "Scatter Plot"], "answer": 2},
        {"q": "What does 'cardinality' mean in a database context?", "options": ["The size of a table in MB", "The number of unique values in a column", "The number of rows in a table", "The depth of a join"], "answer": 1},
        {"q": "What is Pearson correlation measuring?", "options": ["Causation between variables", "Linear relationship strength between two variables", "Rank-based relationship", "Non-linear association"], "answer": 1},
        {"q": "What is the purpose of data normalization?", "options": ["To remove duplicate rows", "To scale features to a comparable range", "To sort data alphabetically", "To encrypt sensitive columns"], "answer": 1},
        {"q": "Which SQL join returns only matching rows from both tables?", "options": ["LEFT JOIN", "RIGHT JOIN", "INNER JOIN", "FULL OUTER JOIN"], "answer": 2},
        {"q": "What is an outlier?", "options": ["A missing value", "A data point significantly different from others", "A duplicate record", "A null entry"], "answer": 1},
        {"q": "What does 'data wrangling' mean?", "options": ["Visualizing data", "Cleaning and transforming raw data into a usable format", "Collecting data from APIs", "Storing data in a warehouse"], "answer": 1},
        {"q": "Which of the following is NOT a data visualization tool?", "options": ["Tableau", "Power BI", "Apache Kafka", "Matplotlib"], "answer": 2},
        {"q": "What is a LEFT JOIN in SQL?", "options": ["Returns only matching rows", "Returns all rows from the left table and matched rows from the right", "Returns all rows from both tables", "Returns only unmatched rows"], "answer": 1},
        {"q": "What does standard deviation measure?", "options": ["The average of a dataset", "The spread or dispersion of values around the mean", "The difference between max and min", "The middle value in a dataset"], "answer": 1},
        {"q": "What is the purpose of GROUP BY in SQL?", "options": ["To filter rows", "To aggregate rows sharing a common value into summary rows", "To sort results", "To join two tables"], "answer": 1},
        {"q": "What is a data warehouse?", "options": ["A place to store raw unprocessed data", "A centralized repository for structured, historical data used for reporting and analysis", "A real-time data streaming platform", "A NoSQL database"], "answer": 1},
        {"q": "What does KPI stand for?", "options": ["Key Process Indicator", "Key Performance Indicator", "Key Product Index", "Key Priority Input"], "answer": 1},
    ],

    "data scientist": [
        {"q": "What is overfitting in machine learning?", "options": ["When a model performs well on unseen data", "When a model memorizes training data but fails on new data", "When a model is too simple", "When training takes too long"], "correct_answers": [1], "explanation": "Overfitting occurs when a model learns the training data too well, including its noise, and fails to generalize to new data."},
        {"q": "What are valid types of recommender systems?", "options": ["Content-based filtering", "Collaborative filtering", "Knowledge-based systems", "All of the above"], "correct_answers": [3], "explanation": "All are valid recommender system types: Content-based uses item features, Collaborative uses user-item patterns, Knowledge-based uses domain expertise."},
        {"q": "What does the bias-variance tradeoff refer to?", "options": ["Speed vs accuracy", "The balance between underfitting and overfitting", "Training size vs test size", "Precision vs recall"], "correct_answers": [1], "explanation": "The bias-variance tradeoff is about balancing a model's tendency to underfit (high bias) vs overfit (high variance)."},
        {"q": "Which metric is best for imbalanced classification datasets?", "options": ["Accuracy", "F1 Score", "Mean Squared Error", "R²"], "correct_answers": [1], "explanation": "F1 Score is ideal for imbalanced datasets because accuracy alone is misleading when classes are imbalanced."},
        {"q": "What is cross-validation used for?", "options": ["Cleaning data", "Estimating model performance on unseen data", "Feature selection", "Hyperparameter logging"], "correct_answers": [1], "explanation": "Cross-validation divides data into folds to get a more robust estimate of model performance."},
        {"q": "What does PCA stand for?", "options": ["Predictive Classification Algorithm", "Principal Component Analysis", "Probabilistic Clustering Approach", "Parallel Computation Architecture"], "correct_answers": [1], "explanation": "PCA is a dimensionality reduction technique that identifies principal components (directions of maximum variance)."},
        {"q": "What is regularization in ML?", "options": ["A technique to speed up training", "A penalty added to reduce model complexity and prevent overfitting", "A data preprocessing step", "A method to increase model accuracy"], "correct_answers": [1], "explanation": "Regularization adds a penalty term to the loss function to discourage overly complex models (L1, L2, etc)."},
        {"q": "What is the purpose of the activation function in a neural network?", "options": ["To initialize weights", "To introduce non-linearity", "To normalize inputs", "To calculate the loss"], "correct_answers": [1], "explanation": "Activation functions introduce non-linearity, allowing neural networks to learn complex patterns."},
        {"q": "Which clustering algorithms are valid choices?", "options": ["K-means", "Hierarchical clustering", "DBSCAN", "All of the above"], "correct_answers": [3], "explanation": "All are valid: K-means partitions data, Hierarchical creates dendrograms, DBSCAN identifies density-based clusters."},
        {"q": "What does 'precision' measure in classification?", "options": ["Of all actual positives, how many were predicted correctly", "Of all predicted positives, how many were actually positive", "The overall accuracy of the model", "The recall of the model"], "correct_answers": [1], "explanation": "Precision = TP / (TP + FP) - of those we predicted as positive, how many were actually positive."},
        {"q": "What is the vanishing gradient problem?", "options": ["Weights becoming too large during training", "Gradients becoming too small, slowing or stopping learning in deep networks", "Loss function not converging", "Overfitting in RNNs"], "correct_answers": [1], "explanation": "In deep networks with sigmoid/tanh activations, gradients can become vanishingly small during backpropagation."},
        {"q": "Which distance metric does KNN use by default?", "options": ["Manhattan", "Cosine", "Euclidean", "Hamming"], "correct_answers": [2], "explanation": "KNN uses Euclidean distance by default, but Manhattan and other metrics can be configured."},
        {"q": "What is a confusion matrix?", "options": ["A matrix showing feature correlations", "A table showing TP, TN, FP, FN for a classifier", "A visualization of decision boundaries", "A weight initialization matrix"], "correct_answers": [1], "explanation": "A confusion matrix shows True Positives, True Negatives, False Positives, and False Negatives for classification evaluation."},
        {"q": "What is the purpose of dropout in neural networks?", "options": ["Speed up forward pass", "Randomly deactivate neurons during training to prevent overfitting", "Initialize weights to zero", "Normalize layer outputs"], "correct_answers": [1], "explanation": "Dropout randomly disables neurons during training, forcing the network to learn redundant representations."},
        {"q": "What is an embedding in NLP?", "options": ["A data augmentation technique", "A dense vector representation of words or tokens", "A tokenization strategy", "A type of attention mechanism"], "correct_answers": [1], "explanation": "Embeddings map discrete tokens (words) to continuous vector spaces that capture semantic relationships."},
        {"q": "What does SMOTE do?", "options": ["Removes outliers", "Generates synthetic samples for the minority class", "Normalizes features", "Reduces dimensionality"], "correct_answers": [1], "explanation": "SMOTE (Synthetic Minority Over-sampling) generates synthetic training samples for underrepresented classes."},
        {"q": "What is the difference between supervised and unsupervised learning?", "options": ["No difference", "Supervised uses labelled data; unsupervised finds patterns in unlabelled data", "Unsupervised is always more accurate", "Supervised doesn't require training data"], "correct_answers": [1], "explanation": "Supervised learning uses labeled data (input-output pairs), while unsupervised finds patterns in unlabeled data."},
        {"q": "What is a ROC curve used for?", "options": ["Visualizing feature importance", "Evaluating classifier performance across all classification thresholds", "Plotting training loss over epochs", "Comparing regression models"], "correct_answers": [1], "explanation": "ROC (Receiver Operating Characteristic) curves show the trade-off between true positive rate and false positive rate."},
        {"q": "What does 'recall' measure in classification?", "options": ["Of all predicted positives, how many were correct", "Of all actual positives, how many were correctly identified", "The overall model accuracy", "The precision of the model"], "correct_answers": [1], "explanation": "Recall = TP / (TP + FN) - of all actual positives, how many did we successfully identify."},
        {"q": "What is gradient descent?", "options": ["A data preprocessing technique", "An optimization algorithm that minimizes a loss function by iteratively updating weights", "A regularization method", "A feature selection approach"], "correct_answers": [1], "explanation": "Gradient descent is the primary optimization algorithm used to train neural networks and many other models."},
        {"q": "What is a hyperparameter?", "options": ["A parameter learned during training", "A configuration value set before training that controls the learning process", "A type of neural network layer", "A metric for model evaluation"], "correct_answers": [1], "explanation": "Hyperparameters (learning rate, batch size, etc.) are set before training and control the learning process."},
    ],

    "ml engineer": [
        {"q": "What is model drift?", "options": ["A bug in the training loop", "Degradation of model performance over time as data distribution changes", "Overfitting on new data", "A hardware failure during inference"], "answer": 1},
        {"q": "What is the purpose of a feature store?", "options": ["To store raw data", "To centrally manage and serve ML features for training and inference", "To log model predictions", "To version control datasets"], "answer": 1},
        {"q": "What does MLflow primarily help with?", "options": ["Data cleaning", "Tracking ML experiments, models and deployments", "Writing neural network code", "Database management"], "answer": 1},
        {"q": "What is A/B testing in the context of ML models?", "options": ["Testing model accuracy", "Comparing two model versions on live traffic to measure performance", "Unit testing ML pipelines", "Validating training data quality"], "answer": 1},
        {"q": "What is quantization in model optimization?", "options": ["Adding more layers", "Reducing model weight precision to decrease size and improve speed", "Increasing training data", "Pruning unused features"], "answer": 1},
        {"q": "What is the purpose of a model registry?", "options": ["To store training datasets", "To track, version and manage trained ML models", "To schedule training jobs", "To monitor data pipelines"], "answer": 1},
        {"q": "What does ONNX stand for?", "options": ["Open Neural Network Exchange", "Online Node Network Execution", "Optimized Numeric Node eXtension", "Object Neural Network eXporter"], "answer": 0},
        {"q": "What is shadow deployment?", "options": ["Deploying a model without monitoring", "Running a new model in parallel with the old one without affecting users", "Deploying to a private cloud", "Rolling back a production model"], "answer": 1},
        {"q": "What is gradient clipping used for?", "options": ["Speed up convergence", "Prevent exploding gradients by capping their magnitude", "Reduce memory usage", "Normalize batch inputs"], "answer": 1},
        {"q": "What is the difference between batch and online learning?", "options": ["No difference", "Batch trains on all data at once; online updates incrementally with new data", "Online is always faster", "Batch learning requires more memory"], "answer": 1},
        {"q": "Which tool is commonly used for orchestrating ML pipelines?", "options": ["Docker", "Apache Airflow", "Redis", "Nginx"], "answer": 1},
        {"q": "What is knowledge distillation?", "options": ["Extracting features from data", "Training a smaller model to mimic a larger model's behaviour", "Compressing a dataset", "A type of transfer learning"], "answer": 1},
        {"q": "What is the purpose of serving infrastructure in ML?", "options": ["To train models faster", "To expose trained models as APIs for real-time or batch predictions", "To store model weights", "To monitor data quality"], "answer": 1},
        {"q": "What is concept drift?", "options": ["A change in model architecture", "A shift in the statistical relationship between inputs and outputs over time", "A training data quality issue", "A deployment failure"], "answer": 1},
        {"q": "What does 'cold start' mean in ML serving?", "options": ["The model is untrained", "Initial latency when a model is first loaded into memory", "A failed model deployment", "Starting training from scratch"], "answer": 1},
        {"q": "What is transfer learning?", "options": ["Copying weights between identical models", "Using a pre-trained model as a starting point for a new but related task", "Transferring data between cloud providers", "A multi-GPU training strategy"], "answer": 1},
        {"q": "What is the purpose of model versioning?", "options": ["To track training dataset size", "To manage and reproduce different iterations of a trained model", "To monitor inference latency", "To schedule retraining jobs"], "answer": 1},
        {"q": "What is feature engineering?", "options": ["Building ML model architectures", "Creating, transforming or selecting input variables to improve model performance", "Tuning hyperparameters", "Deploying models to production"], "answer": 1},
        {"q": "What does 'data leakage' mean in ML?", "options": ["Sensitive data being exposed externally", "When information from outside the training set improperly influences the model", "Loss of training data due to hardware failure", "Overfitting on the validation set"], "answer": 1},
        {"q": "What is the purpose of a confusion matrix in model evaluation?", "options": ["To visualize feature correlations", "To break down classifier predictions into TP, TN, FP, FN for detailed analysis", "To plot loss curves", "To compare model sizes"], "answer": 1},
    ],

    "frontend developer": [
        {"q": "What does the CSS box model consist of?", "options": ["margin, border, padding, content", "width, height, color, font", "display, position, float, clear", "flex, grid, block, inline"], "answer": 0},
        {"q": "What is the virtual DOM?", "options": ["A browser feature", "A lightweight copy of the real DOM used by frameworks like React to optimize updates", "A server-side rendering technique", "A CSS-in-JS library"], "answer": 1},
        {"q": "What does 'async/await' do in JavaScript?", "options": ["Runs code in parallel threads", "Simplifies working with Promises for asynchronous code", "Blocks the main thread", "Creates web workers"], "answer": 1},
        {"q": "What is CSS specificity?", "options": ["How fast CSS is parsed", "The priority system that determines which CSS rule applies to an element", "The number of CSS rules in a file", "The order of CSS imports"], "answer": 1},
        {"q": "What is the difference between == and === in JavaScript?", "options": ["No difference", "== checks value only; === checks value and type", "=== is slower", "== is only for numbers"], "answer": 1},
        {"q": "What is lazy loading?", "options": ["Caching assets aggressively", "Deferring loading of non-critical resources until they are needed", "Pre-loading all assets at startup", "A CSS animation technique"], "answer": 1},
        {"q": "What is a closure in JavaScript?", "options": ["A way to close browser windows", "A function that retains access to its outer scope even after the outer function returns", "An event handler pattern", "A module import technique"], "answer": 1},
        {"q": "What does 'semantic HTML' mean?", "options": ["HTML with inline styles", "Using HTML elements that convey meaning about content (e.g. <article>, <nav>)", "Minimized HTML", "HTML generated by JavaScript"], "answer": 1},
        {"q": "What is the purpose of the 'key' prop in React lists?", "options": ["Styling list items", "Helping React identify which items changed, were added or removed", "Setting list item order", "Enabling animations"], "answer": 1},
        {"q": "What is CORS?", "options": ["A CSS framework", "A browser security mechanism controlling cross-origin HTTP requests", "A JavaScript build tool", "A REST API standard"], "answer": 1},
        {"q": "What is code splitting?", "options": ["Splitting CSS from JS", "Dividing a bundle into smaller chunks loaded on demand", "Separating dev and prod configs", "Breaking a component into subcomponents"], "answer": 1},
        {"q": "What does 'debouncing' do?", "options": ["Removes event listeners", "Delays a function call until a pause in events occurs", "Throttles API calls to one per second", "Prevents default browser behaviour"], "answer": 1},
        {"q": "What is the purpose of a service worker?", "options": ["To run server-side code", "To enable offline capabilities and background tasks in web apps", "To manage CSS animations", "To handle database queries"], "answer": 1},
        {"q": "What is tree shaking?", "options": ["Removing unused CSS", "Eliminating dead code from JavaScript bundles during build", "Optimizing image assets", "Splitting large components"], "answer": 1},
        {"q": "What does 'hydration' mean in SSR frameworks?", "options": ["Fetching data on the server", "Attaching JavaScript event listeners to server-rendered HTML on the client", "Caching rendered pages", "Pre-rendering static pages"], "answer": 1},
        {"q": "What is the difference between let, const and var in JavaScript?", "options": ["No difference", "var is function-scoped; let and const are block-scoped; const cannot be reassigned", "const is the fastest", "let is only for numbers"], "answer": 1},
        {"q": "What is the purpose of CSS Flexbox?", "options": ["To create 3D animations", "To lay out elements in a one-dimensional row or column with flexible sizing", "To style typography", "To manage z-index stacking"], "answer": 1},
        {"q": "What is event bubbling in JavaScript?", "options": ["Creating custom events", "When an event triggered on a child element propagates up through ancestor elements", "Preventing default event behaviour", "Attaching multiple listeners to one element"], "answer": 1},
        {"q": "What is a CSS media query used for?", "options": ["Fetching data based on device type", "Applying different styles based on screen size or device characteristics", "Animating elements on scroll", "Loading different JavaScript files per device"], "answer": 1},
        {"q": "What does the React useEffect hook do?", "options": ["Manages component state", "Runs side effects after render, such as data fetching or subscriptions", "Memoizes expensive calculations", "Creates context for global state"], "answer": 1},
    ],

    "backend developer": [
        {"q": "What is connection pooling?", "options": ["Caching database query results", "Reusing a pool of database connections to reduce overhead", "Load balancing between servers", "Encrypting database connections"], "answer": 1},
        {"q": "What is the difference between authentication and authorization?", "options": ["No difference", "Authentication verifies identity; authorization determines permissions", "Authorization happens before authentication", "Authentication is only for APIs"], "answer": 1},
        {"q": "What is a message queue used for?", "options": ["Storing database records", "Decoupling services by passing messages asynchronously between them", "Load balancing HTTP requests", "Caching API responses"], "answer": 1},
        {"q": "What does idempotency mean for HTTP methods?", "options": ["The response is always the same", "Calling the method multiple times produces the same result as calling once", "The request is always cached", "The method requires no authentication"], "answer": 1},
        {"q": "What is the N+1 query problem?", "options": ["Running N queries in parallel", "Making 1 query to fetch a list then N additional queries for each item", "A query timeout issue", "A deadlock caused by multiple queries"], "answer": 1},
        {"q": "What is JWT used for?", "options": ["Encrypting database passwords", "Securely transmitting claims between parties as a signed token", "Hashing user passwords", "Compressing API responses"], "answer": 1},
        {"q": "What is the difference between SQL and NoSQL databases?", "options": ["SQL is faster", "SQL uses structured schemas and relations; NoSQL is flexible and schema-less", "NoSQL supports ACID transactions by default", "SQL is only for small datasets"], "answer": 1},
        {"q": "What is rate limiting?", "options": ["Compressing API responses", "Restricting how many requests a client can make in a time window", "Caching frequent queries", "Validating API inputs"], "answer": 1},
        {"q": "What is a reverse proxy?", "options": ["A client-side caching layer", "A server that forwards client requests to backend servers", "A database middleware", "A firewall component"], "answer": 1},
        {"q": "What does ACID stand for in databases?", "options": ["Atomicity, Consistency, Isolation, Durability", "Availability, Consistency, Integrity, Distribution", "Atomicity, Concurrency, Indexing, Durability", "Authentication, Consistency, Isolation, Deployment"], "answer": 0},
        {"q": "What is caching and why is it used?", "options": ["Storing data permanently", "Temporarily storing frequently accessed data to reduce latency and load", "Encrypting sensitive data", "Compressing large responses"], "answer": 1},
        {"q": "What is a webhook?", "options": ["A scheduled API poll", "An HTTP callback triggered when an event occurs in a service", "A type of WebSocket", "A reverse proxy endpoint"], "answer": 1},
        {"q": "What is eventual consistency?", "options": ["Data is always consistent immediately", "Given no new updates, all replicas will eventually return the same value", "Consistency is never guaranteed", "A SQL isolation level"], "answer": 1},
        {"q": "What is the purpose of an ORM?", "options": ["To optimize raw SQL queries", "To map database tables to programming language objects", "To visualize database schemas", "To enforce foreign key constraints"], "answer": 1},
        {"q": "What is horizontal scaling?", "options": ["Upgrading a single server's hardware", "Adding more servers to distribute load", "Increasing database storage", "Compressing application code"], "answer": 1},
        {"q": "What is a database transaction?", "options": ["A single SQL SELECT query", "A unit of work that is executed atomically — all steps succeed or all are rolled back", "A scheduled database backup", "A connection between two databases"], "answer": 1},
        {"q": "What is the purpose of an API gateway?", "options": ["To store API responses", "To act as a single entry point managing routing, auth and rate limiting for APIs", "To generate API documentation", "To test API endpoints"], "answer": 1},
        {"q": "What is gRPC?", "options": ["A REST API standard", "A high-performance RPC framework using Protocol Buffers for service communication", "A database query language", "A load balancing algorithm"], "answer": 1},
        {"q": "What is database sharding?", "options": ["Encrypting a database", "Partitioning a database horizontally across multiple servers to distribute load", "Creating database indexes", "Replicating a database for backups"], "answer": 1},
        {"q": "What is the purpose of environment variables in a backend application?", "options": ["To style the application", "To store configuration and secrets outside source code for security and flexibility", "To define database schemas", "To manage package dependencies"], "answer": 1},
    ],

    "devops engineer": [
        {"q": "What is Infrastructure as Code (IaC)?", "options": ["Writing application code", "Managing infrastructure through machine-readable config files", "Automating code reviews", "A cloud pricing model"], "answer": 1},
        {"q": "What does a Dockerfile define?", "options": ["Network configuration", "Steps to build a Docker container image", "Kubernetes deployment specs", "CI/CD pipeline stages"], "answer": 1},
        {"q": "What is the purpose of Kubernetes?", "options": ["Building Docker images", "Orchestrating, scaling and managing containerized applications", "Writing infrastructure code", "Monitoring application logs"], "answer": 1},
        {"q": "What is blue-green deployment?", "options": ["A CI/CD tool", "Running two identical environments, switching traffic to the new version after validation", "A Docker networking mode", "A load balancing algorithm"], "answer": 1},
        {"q": "What is the purpose of a CI/CD pipeline?", "options": ["To write unit tests", "To automate building, testing and deploying code changes", "To manage cloud costs", "To provision servers"], "answer": 1},
        {"q": "What is a Kubernetes Pod?", "options": ["A virtual machine", "The smallest deployable unit in Kubernetes, containing one or more containers", "A Kubernetes cluster", "A network namespace"], "answer": 1},
        {"q": "What does Terraform do?", "options": ["Monitors application performance", "Provisions and manages cloud infrastructure using declarative config", "Builds Docker images", "Runs CI pipelines"], "answer": 1},
        {"q": "What is the difference between a container and a VM?", "options": ["No difference", "Containers share the host OS kernel; VMs have their own full OS", "VMs are faster to start", "Containers require more memory"], "answer": 1},
        {"q": "What is a Helm chart?", "options": ["A Grafana dashboard", "A package manager template for Kubernetes applications", "A Docker Compose file", "A CI/CD workflow definition"], "answer": 1},
        {"q": "What is observability in DevOps?", "options": ["Writing more logs", "The ability to understand system state through metrics, logs and traces", "Monitoring server uptime only", "Automated testing coverage"], "answer": 1},
        {"q": "What does 'shift left' mean in DevOps?", "options": ["Moving deployment to earlier in the week", "Integrating testing and security earlier in the development lifecycle", "Reducing infrastructure cost", "Moving to microservices"], "answer": 1},
        {"q": "What is a rolling deployment?", "options": ["Deploying to all instances simultaneously", "Gradually replacing old instances with new ones to avoid downtime", "A failed deployment rollback", "Deploying to a staging environment"], "answer": 1},
        {"q": "What is the purpose of Prometheus?", "options": ["Container orchestration", "Collecting and storing time-series metrics for monitoring", "Log aggregation", "Service mesh management"], "answer": 1},
        {"q": "What is a service mesh?", "options": ["A Kubernetes networking plugin", "An infrastructure layer handling service-to-service communication, security and observability", "A load balancer configuration", "A Docker network driver"], "answer": 1},
        {"q": "What does 'immutable infrastructure' mean?", "options": ["Infrastructure that never changes configuration", "Servers are replaced rather than updated in place", "Infrastructure with no downtime", "Read-only file systems"], "answer": 1},
        {"q": "What is the purpose of a Kubernetes ConfigMap?", "options": ["To store container images", "To store non-sensitive configuration data that pods can consume", "To manage network policies", "To define resource limits for pods"], "answer": 1},
        {"q": "What is canary deployment?", "options": ["Deploying to all users at once", "Rolling out a change to a small subset of users before a full release", "A Kubernetes deployment strategy for stateful apps", "Deploying only to staging"], "answer": 1},
        {"q": "What is the purpose of a load balancer in a Kubernetes cluster?", "options": ["To build Docker images", "To distribute incoming traffic across multiple pods or nodes", "To store persistent data", "To manage secrets"], "answer": 1},
        {"q": "What is Ansible used for?", "options": ["Container orchestration", "Automating configuration management, application deployment and task execution", "Building CI pipelines", "Monitoring infrastructure"], "answer": 1},
        {"q": "What is a Kubernetes Secret?", "options": ["An encrypted database", "An object for storing sensitive data like passwords and API keys for use by pods", "A private container registry", "An RBAC policy"], "answer": 1},
    ],

    "full stack developer": [
        {"q": "What is the difference between server-side and client-side rendering?", "options": ["No difference", "SSR generates HTML on the server; CSR renders in the browser using JS", "CSR is always faster", "SSR only works with React"], "answer": 1},
        {"q": "What is a RESTful API?", "options": ["An API using GraphQL", "An API following REST constraints using HTTP methods and stateless communication", "A WebSocket-based API", "An RPC-style API"], "answer": 1},
        {"q": "What is the purpose of environment variables?", "options": ["To style components", "To store configuration and secrets outside of source code", "To manage dependencies", "To define database schemas"], "answer": 1},
        {"q": "What is CORS and when is it needed?", "options": ["A CSS framework", "A browser policy; needed when a frontend on one origin requests another origin's API", "A backend caching strategy", "An authentication protocol"], "answer": 1},
        {"q": "What is the purpose of a .gitignore file?", "options": ["To list contributors", "To specify files and folders Git should not track", "To define CI/CD pipelines", "To configure git hooks"], "answer": 1},
        {"q": "What is WebSocket used for?", "options": ["REST API communication", "Full-duplex real-time communication between client and server", "Static file serving", "Database querying"], "answer": 1},
        {"q": "What does npm install do?", "options": ["Runs the application", "Installs dependencies listed in package.json", "Builds the application for production", "Updates Node.js version"], "answer": 1},
        {"q": "What is the purpose of a load balancer?", "options": ["To cache database queries", "To distribute incoming traffic across multiple servers", "To compress API responses", "To manage SSL certificates"], "answer": 1},
        {"q": "What is the difference between cookies and localStorage?", "options": ["No difference", "Cookies are sent with HTTP requests and can expire; localStorage persists in browser only", "localStorage is more secure", "Cookies can only store strings"], "answer": 1},
        {"q": "What is GraphQL?", "options": ["A SQL variant", "A query language for APIs allowing clients to request exactly the data they need", "A NoSQL database", "A REST alternative using XML"], "answer": 1},
        {"q": "What is middleware in Express.js?", "options": ["A database connector", "A function that processes requests between receiving and sending a response", "A frontend routing library", "A WebSocket handler"], "answer": 1},
        {"q": "What is the purpose of a CDN?", "options": ["To run backend code closer to users", "To serve static assets from servers geographically close to users", "To manage DNS records", "To provide database replication"], "answer": 1},
        {"q": "What is an ORM?", "options": ["A REST framework", "A library mapping database tables to code objects", "An object serialization format", "A query caching layer"], "answer": 1},
        {"q": "What is the event loop in Node.js?", "options": ["A for loop variant", "The mechanism that handles asynchronous callbacks in a single-threaded environment", "A real-time data stream", "A Node.js testing utility"], "answer": 1},
        {"q": "What does Docker Compose do?", "options": ["Builds Docker images", "Defines and runs multi-container Docker applications from a YAML file", "Deploys containers to Kubernetes", "Monitors container performance"], "answer": 1},
        {"q": "What is the purpose of JWT in a full stack application?", "options": ["Styling components", "Securely passing user identity between frontend and backend after authentication", "Compressing API payloads", "Managing database connections"], "answer": 1},
        {"q": "What is the difference between GET and POST HTTP methods?", "options": ["No difference", "GET retrieves data; POST submits data to create or update a resource", "POST is more secure than GET by default", "GET can send a request body"], "answer": 1},
        {"q": "What is SSR (Server-Side Rendering) good for?", "options": ["Reducing server load", "Improving initial page load time and SEO by delivering fully rendered HTML", "Eliminating the need for a backend", "Replacing REST APIs"], "answer": 1},
        {"q": "What is the purpose of a package.json file?", "options": ["To configure the database", "To define project metadata, scripts and dependencies for a Node.js project", "To store environment variables", "To define Docker containers"], "answer": 1},
        {"q": "What is the difference between SQL and NoSQL in a full stack context?", "options": ["SQL is always better", "SQL suits structured relational data; NoSQL suits flexible, unstructured or rapidly changing data", "NoSQL is only for large companies", "SQL cannot scale horizontally"], "answer": 1},
    ],

    "cybersecurity analyst": [
        {"q": "What is SQL injection?", "options": ["A database optimization technique", "An attack inserting malicious SQL into queries to manipulate databases", "A method to speed up queries", "A database backup method"], "answer": 1},
        {"q": "What is the purpose of a firewall?", "options": ["To speed up network traffic", "To monitor and control incoming and outgoing network traffic based on rules", "To encrypt data in transit", "To store network logs"], "answer": 1},
        {"q": "What is phishing?", "options": ["A network scanning technique", "A social engineering attack tricking users into revealing sensitive information", "A malware type", "A password cracking method"], "answer": 1},
        {"q": "What does XSS stand for?", "options": ["Cross-Site Scripting", "Cross-Server Synchronization", "External Session Security", "Extended Security Schema"], "answer": 0},
        {"q": "What is a zero-day vulnerability?", "options": ["A vulnerability with no fix available yet", "A vulnerability fixed on the same day it's found", "A low-severity bug", "A known vulnerability older than one year"], "answer": 0},
        {"q": "What is the principle of least privilege?", "options": ["Users should have maximum access", "Grant users only the minimum access needed to do their job", "Admins should share credentials", "Systems should run as root"], "answer": 1},
        {"q": "What is a Man-in-the-Middle attack?", "options": ["An insider threat", "An attacker secretly intercepting and possibly altering communication between two parties", "A DDoS attack variant", "A brute force attack"], "answer": 1},
        {"q": "What is the purpose of hashing passwords?", "options": ["To encrypt them for decryption later", "To store a non-reversible representation so plaintext is never stored", "To compress them", "To speed up login"], "answer": 1},
        {"q": "What is a DDoS attack?", "options": ["Stealing user data from a database", "Overwhelming a server with massive traffic to make it unavailable", "Injecting malicious code into a site", "Intercepting network traffic"], "answer": 1},
        {"q": "What is two-factor authentication (2FA)?", "options": ["Two passwords required", "A second verification step beyond a password (e.g. OTP, biometric)", "Logging in from two devices", "Encrypting login sessions twice"], "answer": 1},
        {"q": "What is a VPN used for?", "options": ["Speeding up internet", "Creating an encrypted tunnel for secure communication over public networks", "Blocking ads", "Storing credentials securely"], "answer": 1},
        {"q": "What is OWASP?", "options": ["A firewall vendor", "An open community producing resources on web application security", "A government cybersecurity agency", "A network monitoring tool"], "answer": 1},
        {"q": "What is social engineering?", "options": ["Hacking through software exploits", "Manipulating people into revealing confidential information", "A network penetration technique", "An encryption bypass method"], "answer": 1},
        {"q": "What is the purpose of penetration testing?", "options": ["To monitor network traffic", "To simulate attacks and identify vulnerabilities before malicious actors do", "To install security patches", "To train employees on security policies"], "answer": 1},
        {"q": "What is encryption?", "options": ["Deleting sensitive files", "Converting data into an unreadable format that can only be reversed with a key", "Compressing files for storage", "Backing up data securely"], "answer": 1},
        {"q": "What is a brute force attack?", "options": ["Exploiting a software vulnerability", "Systematically trying all possible passwords or keys until the correct one is found", "Intercepting network packets", "Injecting malicious scripts"], "answer": 1},
        {"q": "What is the difference between symmetric and asymmetric encryption?", "options": ["No difference", "Symmetric uses one shared key; asymmetric uses a public-private key pair", "Asymmetric is faster", "Symmetric requires more computing power"], "answer": 1},
        {"q": "What is a security audit?", "options": ["Automated vulnerability scanning only", "A systematic evaluation of an organization's security posture against standards and policies", "Installing security patches", "Monitoring network traffic in real time"], "answer": 1},
        {"q": "What does CSRF stand for?", "options": ["Cross-Site Request Forgery", "Client-Side Request Filtering", "Cross-Server Response Failure", "Centralized Security Request Framework"], "answer": 0},
        {"q": "What is the purpose of an Intrusion Detection System (IDS)?", "options": ["To block all incoming traffic", "To monitor network or system activity and alert on suspicious behaviour", "To encrypt sensitive data", "To manage user access controls"], "answer": 1},
    ],

    "default": [
        {"q": "What is the time complexity of binary search?", "options": ["O(n)", "O(log n)", "O(n²)", "O(1)"], "answer": 1},
        {"q": "Which data structure uses LIFO order?", "options": ["Queue", "Stack", "Heap", "Linked List"], "answer": 1},
        {"q": "What does SQL stand for?", "options": ["Structured Query Language", "Simple Query Logic", "Sequential Query List", "Standard Query Language"], "answer": 0},
        {"q": "Which sorting algorithm has O(n log n) average time complexity?", "options": ["Bubble Sort", "Insertion Sort", "Merge Sort", "Selection Sort"], "answer": 2},
        {"q": "What is the output of 2 ** 3 in Python?", "options": ["6", "8", "9", "5"], "answer": 1},
        {"q": "Which keyword defines a function in Python?", "options": ["function", "def", "fun", "define"], "answer": 1},
        {"q": "O(1) refers to:", "options": ["Linear time", "Logarithmic time", "Constant time", "Quadratic time"], "answer": 2},
        {"q": "Best data structure for a priority queue?", "options": ["Array", "Stack", "Heap", "Linked List"], "answer": 2},
        {"q": "What is a primary key in a relational database?", "options": ["A key that can be null", "Unique identifier for each record", "A foreign reference", "An indexed column"], "answer": 1},
        {"q": "Which HTTP method updates a resource?", "options": ["GET", "POST", "PUT", "DELETE"], "answer": 2},
        {"q": "What is polymorphism in OOP?", "options": ["Multiple inheritance", "The ability of different objects to respond to the same interface differently", "Hiding internal data", "Creating objects from classes"], "answer": 1},
        {"q": "What is a foreign key?", "options": ["A key from another country", "A column that references a primary key in another table", "An encrypted key", "A composite key"], "answer": 1},
        {"q": "What is the purpose of version control?", "options": ["To speed up code execution", "To track changes to code over time and collaborate safely", "To test code automatically", "To deploy applications"], "answer": 1},
        {"q": "What does API stand for?", "options": ["Application Programming Interface", "Automated Program Integration", "Advanced Protocol Interface", "Application Process Interaction"], "answer": 0},
        {"q": "What is a linked list?", "options": ["An array with fixed size", "A sequence of nodes where each points to the next", "A sorted array", "A hash-based structure"], "answer": 1},
        {"q": "What does OOP stand for?", "options": ["Object-Oriented Programming", "Open Object Protocol", "Operational Output Processing", "Optional Object Pattern"], "answer": 0},
        {"q": "What is recursion?", "options": ["A loop that runs forever", "A function that calls itself to solve a smaller instance of the same problem", "A type of sorting algorithm", "A memory management technique"], "answer": 1},
        {"q": "What is the difference between a stack and a queue?", "options": ["No difference", "Stack is LIFO (last in, first out); queue is FIFO (first in, first out)", "Queue is always faster", "Stack can only store integers"], "answer": 1},
        {"q": "What is encapsulation in OOP?", "options": ["Inheriting from a parent class", "Bundling data and methods together while restricting direct access to internal details", "Creating multiple instances of a class", "Overriding parent class methods"], "answer": 1},
        {"q": "What does HTTP stand for?", "options": ["HyperText Transfer Protocol", "High-Traffic Transmission Protocol", "Hosted Text Transfer Program", "HyperText Transmission Process"], "answer": 0},
    ],
}

# ═══════════════════════════════════════════════════════════════════════════════
# CODING QUESTION POOLS — keyed by role keyword
# ═══════════════════════════════════════════════════════════════════════════════

CODING_POOLS = {

    "data analyst": [
        {
            "id": "find_average",
            "func": "find_average",
            "title": "Find Average of List",
            "difficulty": "Easy",
            "description": "Given a list of numbers, return the average (mean) as a float. Return 0.0 if the list is empty.\n\nExample:\n  Input:  [10, 20, 30]\n  Output: 20.0",
            "starter": "def find_average(nums):\n    # write your solution here\n    pass\n",
            "test_cases": [
                {"input": ([10, 20, 30],), "expected": 20.0},
                {"input": ([5, 5, 5, 5],), "expected": 5.0},
                {"input": ([],),           "expected": 0.0},
            ],
        },
        {
            "id": "count_duplicates",
            "func": "count_duplicates",
            "title": "Count Duplicates",
            "difficulty": "Easy",
            "description": "Given a list, return the count of elements that appear more than once.\n\nExample:\n  Input:  [1, 2, 2, 3, 3, 3]\n  Output: 2  (2 and 3 are duplicates)",
            "starter": "def count_duplicates(nums):\n    # write your solution here\n    pass\n",
            "test_cases": [
                {"input": ([1, 2, 2, 3, 3, 3],), "expected": 2},
                {"input": ([1, 2, 3],),           "expected": 0},
                {"input": ([1, 1, 1, 1],),        "expected": 1},
            ],
        },
        {
            "id": "most_frequent",
            "func": "most_frequent",
            "title": "Most Frequent Element",
            "difficulty": "Easy",
            "description": "Given a non-empty list, return the element that appears most frequently. If there is a tie, return the smallest element.\n\nExample:\n  Input:  [1, 2, 2, 3, 3]\n  Output: 2",
            "starter": "def most_frequent(nums):\n    # write your solution here\n    pass\n",
            "test_cases": [
                {"input": ([1, 2, 2, 3, 3],), "expected": 2},
                {"input": ([4, 4, 4, 1],),    "expected": 4},
                {"input": ([7],),             "expected": 7},
            ],
        },
        {
            "id": "flatten_list",
            "func": "flatten_list",
            "title": "Flatten a Nested List",
            "difficulty": "Easy",
            "description": "Given a list of lists, return a single flat list containing all elements.\n\nExample:\n  Input:  [[1, 2], [3, 4], [5]]\n  Output: [1, 2, 3, 4, 5]",
            "starter": "def flatten_list(nested):\n    # write your solution here\n    pass\n",
            "test_cases": [
                {"input": ([[1, 2], [3, 4], [5]],), "expected": [1, 2, 3, 4, 5]},
                {"input": ([[10, 20], [30]],),      "expected": [10, 20, 30]},
                {"input": ([[],  [1]],),            "expected": [1]},
            ],
        },
    ],

    "data scientist": [
        {
            "id": "normalize",
            "func": "normalize",
            "title": "Min-Max Normalization",
            "difficulty": "Easy",
            "description": "Given a list of numbers, return a new list with values normalized to [0, 1] using min-max scaling.\nIf all values are the same, return a list of 0.0s.\n\nExample:\n  Input:  [0, 5, 10]\n  Output: [0.0, 0.5, 1.0]",
            "starter": "def normalize(nums):\n    # write your solution here\n    pass\n",
            "test_cases": [
                {"input": ([0, 5, 10],),   "expected": [0.0, 0.5, 1.0]},
                {"input": ([1, 1, 1],),    "expected": [0.0, 0.0, 0.0]},
                {"input": ([2, 4],),       "expected": [0.0, 1.0]},
            ],
        },
        {
            "id": "running_mean",
            "func": "running_mean",
            "title": "Running Mean",
            "difficulty": "Easy",
            "description": "Given a list of numbers, return a list where each element is the mean of all elements up to and including that index.\n\nExample:\n  Input:  [1, 2, 3, 4]\n  Output: [1.0, 1.5, 2.0, 2.5]",
            "starter": "def running_mean(nums):\n    # write your solution here\n    pass\n",
            "test_cases": [
                {"input": ([1, 2, 3, 4],), "expected": [1.0, 1.5, 2.0, 2.5]},
                {"input": ([5, 5],),       "expected": [5.0, 5.0]},
                {"input": ([10],),         "expected": [10.0]},
            ],
        },
        {
            "id": "count_above_mean",
            "func": "count_above_mean",
            "title": "Count Elements Above Mean",
            "difficulty": "Easy",
            "description": "Given a list of numbers, return how many elements are strictly above the mean.\n\nExample:\n  Input:  [1, 2, 3, 4, 5]\n  Output: 2",
            "starter": "def count_above_mean(nums):\n    # write your solution here\n    pass\n",
            "test_cases": [
                {"input": ([1, 2, 3, 4, 5],), "expected": 2},
                {"input": ([10, 10, 10],),     "expected": 0},
                {"input": ([1, 100],),         "expected": 1},
            ],
        },
        {
            "id": "remove_outliers",
            "func": "remove_outliers",
            "title": "Remove Outliers",
            "difficulty": "Easy",
            "description": "Given a list of numbers, remove values more than 2 standard deviations from the mean and return the cleaned list.\n\nExample:\n  Input:  [10, 12, 11, 100, 10]\n  Output: [10, 12, 11, 10]",
            "starter": "def remove_outliers(nums):\n    # write your solution here\n    pass\n",
            "test_cases": [
                {"input": ([10, 12, 11, 100, 10],), "expected": [10, 12, 11, 10]},
                {"input": ([1, 2, 3, 4, 5],),       "expected": [1, 2, 3, 4, 5]},
                {"input": ([50, 51, 49, 200],),      "expected": [50, 51, 49]},
            ],
        },
    ],

    "cybersecurity analyst": [
        {
            "id": "is_strong_password",
            "func": "is_strong_password",
            "title": "Strong Password Checker",
            "difficulty": "Easy",
            "description": "Return True if the password is strong: at least 8 characters, contains an uppercase letter, a lowercase letter, a digit, and a special character (!@#$%^&*).\n\nExample:\n  Input:  'Secure@1'\n  Output: True",
            "starter": "def is_strong_password(password):\n    # write your solution here\n    pass\n",
            "test_cases": [
                {"input": ("Secure@1",),   "expected": True},
                {"input": ("password",),   "expected": False},
                {"input": ("Short@1",),    "expected": False},
                {"input": ("Abcdefg!1",),  "expected": True},
            ],
        },
        {
            "id": "caesar_cipher",
            "func": "caesar_cipher",
            "title": "Caesar Cipher",
            "difficulty": "Easy",
            "description": "Implement a Caesar cipher that shifts each letter by n positions. Non-letter characters stay unchanged. Case is preserved.\n\nExample:\n  Input:  'Hello', 3\n  Output: 'Khoor'",
            "starter": "def caesar_cipher(text, n):\n    # write your solution here\n    pass\n",
            "test_cases": [
                {"input": ("Hello", 3),   "expected": "Khoor"},
                {"input": ("abc", 1),     "expected": "bcd"},
                {"input": ("xyz", 3),     "expected": "abc"},
                {"input": ("Hi!", 1),     "expected": "Ij!"},
            ],
        },
        {
            "id": "mask_sensitive",
            "func": "mask_sensitive",
            "title": "Mask Sensitive Data",
            "difficulty": "Easy",
            "description": "Given a string representing a credit card number (digits only), return a masked version where all but the last 4 digits are replaced with '*'.\n\nExample:\n  Input:  '1234567812345678'\n  Output: '************5678'",
            "starter": "def mask_sensitive(card_number):\n    # write your solution here\n    pass\n",
            "test_cases": [
                {"input": ("1234567812345678",), "expected": "************5678"},
                {"input": ("1111222233334444",), "expected": "************4444"},
                {"input": ("0000",),             "expected": "0000"},
            ],
        },
        {
            "id": "count_failed_logins",
            "func": "count_failed_logins",
            "title": "Detect Brute Force",
            "difficulty": "Easy",
            "description": "Given a list of login attempts as strings ('success' or 'fail'), return True if there are 3 or more consecutive failures.\n\nExample:\n  Input:  ['fail', 'fail', 'fail', 'success']\n  Output: True",
            "starter": "def count_failed_logins(attempts):\n    # write your solution here\n    pass\n",
            "test_cases": [
                {"input": (["fail", "fail", "fail", "success"],), "expected": True},
                {"input": (["fail", "success", "fail", "fail"],), "expected": False},
                {"input": (["success", "success"],),              "expected": False},
                {"input": (["fail", "fail", "fail", "fail"],),   "expected": True},
            ],
        },
    ],

    "default": [
        {
            "id": "two_sum",
            "func": "two_sum",
            "title": "Two Sum",
            "difficulty": "Easy",
            "description": "Given an array of integers nums and an integer target, return the indices of the two numbers that add up to target. Each input has exactly one solution.\n\nExample:\n  Input:  nums = [2, 7, 11, 15], target = 9\n  Output: [0, 1]",
            "starter": "def two_sum(nums, target):\n    # write your solution here\n    pass\n",
            "test_cases": [
                {"input": ([2, 7, 11, 15], 9), "expected": [0, 1]},
                {"input": ([3, 2, 4], 6),       "expected": [1, 2]},
                {"input": ([3, 3], 6),           "expected": [0, 1]},
            ],
        },
        {
            "id": "palindrome",
            "func": "is_palindrome",
            "title": "Valid Palindrome",
            "difficulty": "Easy",
            "description": "Given a string s, return True if it is a palindrome after removing non-alphanumeric characters and lowercasing, else False.\n\nExample:\n  Input:  'A man, a plan, a canal: Panama'\n  Output: True",
            "starter": "def is_palindrome(s):\n    # write your solution here\n    pass\n",
            "test_cases": [
                {"input": ("A man, a plan, a canal: Panama",), "expected": True},
                {"input": ("race a car",),                      "expected": False},
                {"input": (" ",),                               "expected": True},
            ],
        },
        {
            "id": "reverse_string",
            "func": "reverse_string",
            "title": "Reverse Words in a String",
            "difficulty": "Easy",
            "description": "Given a string, reverse the order of words (words are separated by spaces). Strip leading/trailing spaces.\n\nExample:\n  Input:  'the sky is blue'\n  Output: 'blue is sky the'",
            "starter": "def reverse_string(s):\n    # write your solution here\n    pass\n",
            "test_cases": [
                {"input": ("the sky is blue",),      "expected": "blue is sky the"},
                {"input": ("  hello world  ",),      "expected": "world hello"},
                {"input": ("a good   example",),     "expected": "example good a"},
            ],
        },
        {
            "id": "max_subarray",
            "func": "max_subarray",
            "title": "Maximum Subarray Sum",
            "difficulty": "Easy",
            "description": "Given an integer array, find the subarray with the largest sum and return that sum (Kadane's algorithm).\n\nExample:\n  Input:  [-2, 1, -3, 4, -1, 2, 1, -5, 4]\n  Output: 6",
            "starter": "def max_subarray(nums):\n    # write your solution here\n    pass\n",
            "test_cases": [
                {"input": ([-2, 1, -3, 4, -1, 2, 1, -5, 4],), "expected": 6},
                {"input": ([1],),                               "expected": 1},
                {"input": ([5, 4, -1, 7, 8],),                 "expected": 23},
            ],
        },
        {
            "id": "fizzbuzz",
            "func": "fizzbuzz",
            "title": "FizzBuzz",
            "difficulty": "Easy",
            "description": "Return a list of strings for numbers 1 to n: 'Fizz' if divisible by 3, 'Buzz' if by 5, 'FizzBuzz' if by both, else the number as a string.\n\nExample:\n  Input:  5\n  Output: ['1','2','Fizz','4','Buzz']",
            "starter": "def fizzbuzz(n):\n    # write your solution here\n    pass\n",
            "test_cases": [
                {"input": (5,),  "expected": ['1','2','Fizz','4','Buzz']},
                {"input": (15,), "expected": ['1','2','Fizz','4','Buzz','Fizz','7','8','Fizz','Buzz','11','Fizz','13','14','FizzBuzz']},
                {"input": (1,),  "expected": ['1']},
            ],
        },
        {
            "id": "valid_brackets",
            "func": "valid_brackets",
            "title": "Valid Brackets",
            "difficulty": "Easy",
            "description": "Given a string containing only '(', ')', '{', '}', '[', ']', return True if the brackets are valid (properly opened and closed in order).\n\nExample:\n  Input:  '()[]{}'\n  Output: True",
            "starter": "def valid_brackets(s):\n    # write your solution here\n    pass\n",
            "test_cases": [
                {"input": ("()[]{}",), "expected": True},
                {"input": ("(]",),     "expected": False},
                {"input": ("{[]}",),   "expected": True},
                {"input": ("([)]",),   "expected": False},
            ],
        },
        {
            "id": "missing_number",
            "func": "missing_number",
            "title": "Find the Missing Number",
            "difficulty": "Easy",
            "description": "Given a list of n distinct numbers in the range [0, n], return the one number missing from the range.\n\nExample:\n  Input:  [3, 0, 1]\n  Output: 2",
            "starter": "def missing_number(nums):\n    # write your solution here\n    pass\n",
            "test_cases": [
                {"input": ([3, 0, 1],),       "expected": 2},
                {"input": ([0, 1],),           "expected": 2},
                {"input": ([9,6,4,2,3,5,7,0,1],), "expected": 8},
            ],
        },
        {
            "id": "anagram_check",
            "func": "is_anagram",
            "title": "Anagram Check",
            "difficulty": "Easy",
            "description": "Given two strings s and t, return True if t is an anagram of s (same characters, same frequency, ignoring case).\n\nExample:\n  Input:  'Anagram', 'nagaram'\n  Output: True",
            "starter": "def is_anagram(s, t):\n    # write your solution here\n    pass\n",
            "test_cases": [
                {"input": ("Anagram", "nagaram"), "expected": True},
                {"input": ("rat", "car"),         "expected": False},
                {"input": ("Listen", "Silent"),   "expected": True},
            ],
        },
    ],
}

# ═══════════════════════════════════════════════════════════════════════════════
# Role keyword aliases — maps pool keys to lists of matching keywords
# ═══════════════════════════════════════════════════════════════════════════════

ROLE_ALIASES = {
    "software engineer":     ["software", "swe", "programmer", "software developer", "application developer"],
    "frontend developer":    ["frontend", "front-end", "react", "vue", "angular", "ui developer", "css", "javascript developer", "web developer"],
    "backend developer":     ["backend", "back-end", "api developer", "server", "node", "django", "flask", "spring", "rails", "golang", "java developer"],
    "full stack developer":  ["full stack", "fullstack", "full-stack", "mern", "mean", "lamp"],
    "data analyst":          ["data analyst", "analyst", "bi developer", "business intelligence", "tableau", "power bi", "reporting"],
    "data scientist":        ["data scientist", "scientist", "machine learning", "ml researcher", "ai researcher", "research scientist"],
    "ml engineer":           ["ml engineer", "mlops", "machine learning engineer", "ai engineer", "deep learning engineer"],
    "devops engineer":       ["devops", "dev ops", "sre", "site reliability", "platform engineer", "cloud engineer", "infrastructure engineer", "kubernetes", "terraform"],
    "cybersecurity analyst": ["security", "cyber", "infosec", "penetration", "pentest", "soc analyst", "security engineer", "security analyst"],
    "mobile developer":      ["android", "ios", "mobile", "flutter", "react native", "kotlin", "swift"],
}


def _resolve_role(role: str) -> str:
    """Map any role string to a pool key using keyword aliases."""
    role_lower = role.lower()

    # Exact pool key match
    if role_lower in MCQ_POOLS:
        return role_lower

    # Alias / keyword match (longer keywords checked first to avoid partial clashes)
    for pool_key, keywords in ROLE_ALIASES.items():
        sorted_kws = sorted(keywords, key=len, reverse=True)
        if any(kw in role_lower for kw in sorted_kws):
            return pool_key

    return "default"


# ═══════════════════════════════════════════════════════════════════════════════
# Question pickers — no-repeat within a session, auto-reset when pool exhausted
# ═══════════════════════════════════════════════════════════════════════════════

def _pick_mcq(role: str, n: int = 10) -> list:
    key  = _resolve_role(role)
    pool = MCQ_POOLS.get(key, MCQ_POOLS["default"])

    seen: set = set(session.get("seen_mcq_ids", []))
    available = [q for q in pool if q["q"] not in seen]

    # Pool exhausted — reset and reuse the full pool
    if len(available) < n:
        seen.clear()
        available = list(pool)

    chosen = random.sample(available, min(n, len(available)))
    seen.update(q["q"] for q in chosen)
    session["seen_mcq_ids"] = list(seen)

    return chosen


def _pick_coding(role: str, n: int = 2) -> list:
    key  = _resolve_role(role)
    pool = CODING_POOLS.get(key, CODING_POOLS["default"])

    seen: set = set(session.get("seen_coding_ids", []))
    available = [q for q in pool if q["id"] not in seen]

    if len(available) < n:
        seen.clear()
        available = list(pool)

    chosen = random.sample(available, min(n, len(available)))
    seen.update(q["id"] for q in chosen)
    session["seen_coding_ids"] = list(seen)

    return chosen


# ═══════════════════════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════════════════════

MCQ_PASS_SCORE  = 60    # %
CODE_PASS_SCORE = 50    # % test cases
MCQ_DURATION    = 600   # seconds (10 min)
CODE_DURATION   = 1200  # seconds (20 min)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("google_login"))
        return f(*args, **kwargs)
    return wrapper


def _run_code(code: str, test_cases: list, func_name: str) -> dict:
    """
    Run code safely. First tries RestrictedPython, falls back to simple exec with numpy/pandas support.
    """
    # Try to import RestrictedPython (preferred method)
    try:
        from restricted_python import compile_restricted, safe_globals
        from restricted_python.guards import safe_builtins, guarded_iter_unpack_sequence
        use_restricted = True
    except ImportError:
        use_restricted = False
    
    if use_restricted:
        # Additional safe builtins for code execution
        SAFE_BUILTINS = safe_builtins.copy()
        SAFE_BUILTINS.update({
            "range": range, "len": len, "enumerate": enumerate, "zip": zip,
            "sorted": sorted, "list": list, "dict": dict, "set": set,
            "int": int, "str": str, "bool": bool, "float": float,
            "abs": abs, "min": min, "max": max, "sum": sum,
            "isinstance": isinstance, "type": type, "tuple": tuple,
            "round": round, "any": any, "all": all,
            "chr": chr, "ord": ord, "map": map, "filter": filter,
            "import": __import__,  # Allow imports
        })
        
        try:
            # Compile with RestrictedPython
            byte_code = compile_restricted(code, "<sandbox>", "exec")
            
            if byte_code.errors:
                error_msg = "; ".join(str(e) for e in byte_code.errors)
                return {"error": f"Syntax error: {error_msg}", "passed": 0, "total": len(test_cases), "results": []}
            
            # Create safe execution namespace
            ns = {
                "__builtins__": SAFE_BUILTINS,
                "_print_": lambda x: repr(x),
                "_getiter_": iter,
                "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
            }
            
            # Execute compiled code
            exec(byte_code, ns)
            
        except SyntaxError as e:
            return {"error": f"Syntax error: {e}", "passed": 0, "total": len(test_cases), "results": []}
        except Exception as e:
            return {"error": f"Execution error: {str(e)[:100]}", "passed": 0, "total": len(test_cases), "results": []}
    
    else:
        # Fallback: Simple exec with safe builtins (when RestrictedPython unavailable)
        SAFE_BUILTINS = {
            "range": range, "len": len, "enumerate": enumerate, "zip": zip,
            "sorted": sorted, "list": list, "dict": dict, "set": set,
            "int": int, "str": str, "bool": bool, "float": float,
            "abs": abs, "min": min, "max": max, "sum": sum,
            "isinstance": isinstance, "type": type, "tuple": tuple,
            "round": round, "any": any, "all": all,
            "chr": chr, "ord": ord, "map": map, "filter": filter,
        }
        
        # Try importing numpy/pandas if available
        try:
            import numpy as np
            SAFE_BUILTINS["np"] = np
            SAFE_BUILTINS["numpy"] = np
        except ImportError:
            pass
        
        try:
            import pandas as pd
            SAFE_BUILTINS["pd"] = pd
            SAFE_BUILTINS["pandas"] = pd
        except ImportError:
            pass
        
        try:
            # Simple exec without RestrictedPython
            ns = {"__builtins__": SAFE_BUILTINS}
            exec(code, ns)
        except SyntaxError as e:
            return {"error": f"Syntax error: {e}", "passed": 0, "total": len(test_cases), "results": []}
        except Exception as e:
            return {"error": f"Execution error: {str(e)[:100]}", "passed": 0, "total": len(test_cases), "results": []}
    
    # Get function from namespace
    fn = ns.get(func_name)
    if fn is None:
        return {"error": f"Function '{func_name}' not found.", "passed": 0, "total": len(test_cases), "results": []}
    
    # Run test cases
    results = []
    for tc in test_cases:
        try:
            # Extract input - handle both list and tuple formats
            test_input = tc.get("input", [])
            if isinstance(test_input, (list, tuple)):
                out = fn(*test_input)
            else:
                out = fn(test_input)
            
            exp = tc["expected"]
            
            # Compare results (handle floating point comparisons and set-like comparisons)
            if isinstance(exp, set):
                ok = set(out) == exp
            elif isinstance(exp, list) and exp and all(isinstance(x, int) for x in exp) and func_name == "two_sum":
                # For two_sum, order doesn't matter - compare as sets
                ok = set(out) == set(exp) if isinstance(out, (list, tuple)) else False
            elif isinstance(exp, list) and exp and isinstance(exp[0], float):
                # Check if all values are within tolerance
                try:
                    ok = len(out) == len(exp) and all(abs(a - b) < 1e-6 for a, b in zip(out, exp))
                except (TypeError, ValueError):
                    ok = out == exp
            else:
                ok = out == exp
            
            results.append({"passed": ok, "output": repr(out)[:100], "expected": repr(exp)[:100]})
        except Exception as e:
            results.append({"passed": False, "output": f"Error: {str(e)[:50]}", "expected": repr(tc["expected"])[:100]})
    
    passed = sum(1 for r in results if r["passed"])
    return {"results": results, "passed": passed, "total": len(test_cases), "error": None}


# ═══════════════════════════════════════════════════════════════════════════════
# LEVEL 1 — MCQ
# ═══════════════════════════════════════════════════════════════════════════════

@screening_bp.route("/screening/level1")
@_login_required
def level1():
    role = request.args.get("role", session.get("pending_role", "Software Engineer"))
    mode = request.args.get("mode", session.get("pending_mode", "chat"))

    session["pending_role"] = role
    session["pending_mode"] = mode
    session["screening_stage"] = 1
    session["mcq_start"] = time.time()

    # Try to generate MCQ questions using AI first
    questions = generate_mcq_questions(role, n=10)
    
    # Retry if first attempt fails
    retry = 0
    while not questions and retry < 2:
        questions = generate_mcq_questions(role, n=10)
        retry += 1
    
    # Fallback to hardcoded MCQ pool if AI generation failed
    if not questions:
        role_lower = role.lower()
        pool_key = None
        
        # Try to find matching pool by role name
        for key in MCQ_POOLS.keys():
            if key.lower() in role_lower or role_lower in key.lower():
                pool_key = key
                break
        
        # Use default pool if no exact match found
        if not pool_key:
            pool_key = "default"
        
        # Sample 10 random questions from the pool
        if pool_key in MCQ_POOLS and MCQ_POOLS[pool_key]:
            questions = random.sample(MCQ_POOLS[pool_key], min(10, len(MCQ_POOLS[pool_key])))
        else:
            # Last resort: use default pool
            questions = random.sample(MCQ_POOLS.get("default", []), min(10, len(MCQ_POOLS.get("default", []))))

    session["mcq_questions"] = questions if questions else []

    return render_template("screening/level1.html",
                           questions=questions, duration=MCQ_DURATION, role=role)


@screening_bp.route("/screening/level1/submit", methods=["POST"])
@_login_required
def level1_submit():
    if session.get("screening_stage") != 1:
        return redirect(url_for("screening.level1"))

    questions = session.get("mcq_questions", [])
    correct, details = 0, []
    for i, q in enumerate(questions):
        try:
            ui = int(request.form.get(f"q{i}", -1))
        except (ValueError, TypeError):
            ui = -1
        
        # Support both old format (single "answer") and new format (list "correct_answers")
        if "correct_answers" in q:
            # New format: multiple valid answers
            ok = ui in q["correct_answers"]
            correct_indices = q["correct_answers"]
        else:
            # Legacy format: single answer (for backward compatibility)
            ok = (ui == q["answer"])
            correct_indices = [q["answer"]]
        
        if ok:
            correct += 1
        
        # Show first correct answer or all if multiple
        if len(correct_indices) == 1:
            correct_answer_text = q["options"][correct_indices[0]]
        else:
            correct_answer_texts = [q["options"][idx] for idx in correct_indices]
            correct_answer_text = " OR ".join(correct_answer_texts)
        
        details.append({
            "question": q["q"],
            "your_answer": q["options"][ui] if 0 <= ui < len(q["options"]) else "Not answered",
            "correct_answer": correct_answer_text,
            "explanation": q.get("explanation", ""),  # Add explanation if available
            "correct": ok,
        })

    pct    = int(correct / len(questions) * 100) if questions else 0
    passed = pct >= MCQ_PASS_SCORE
    session.update({"mcq_score": pct, "mcq_details": details, "mcq_passed": passed,
                    "screening_stage": 2 if passed else 0})
    return redirect(url_for("screening.level1_result"))


@screening_bp.route("/screening/level1/result")
@_login_required
def level1_result():
    return render_template("screening/level1_result.html",
                           score=session.get("mcq_score", 0),
                           passed=session.get("mcq_passed", False),
                           details=session.get("mcq_details", []),
                           cutoff=MCQ_PASS_SCORE,
                           role=session.get("pending_role", ""))


# ═══════════════════════════════════════════════════════════════════════════════
# LEVEL 2 — Coding
# ═══════════════════════════════════════════════════════════════════════════════

@screening_bp.route("/screening/level2")
@_login_required
def level2():
    if session.get("screening_stage") != 2:
        return redirect(url_for("home"))

    role = session.get("pending_role", "Software Engineer")
    session["code_start"] = time.time()
    
    # Use hardcoded coding pool matched to role
    questions = _pick_coding(role, n=2)
    
    session["coding_questions"] = questions if questions else []

    return render_template("screening/level2.html",
                           questions=questions, duration=CODE_DURATION, role=role)


@screening_bp.route("/screening/level2/submit", methods=["POST"])
@_login_required
def level2_submit():
    if session.get("screening_stage") != 2:
        return redirect(url_for("home"))

    questions = session.get("coding_questions", _pick_coding(session.get("pending_role", ""), n=2))
    total_p, total_t, code_results = 0, 0, []

    for cq in questions:
        code = request.form.get(f"code_{cq['id']}", "").strip()
        res  = _run_code(code, cq["test_cases"], cq["func"])
        code_results.append({"title": cq["title"], "difficulty": cq["difficulty"],
                              "result": res, "code": code})
        total_p += res.get("passed", 0)
        total_t += res.get("total", len(cq["test_cases"]))

    pct    = int(total_p / total_t * 100) if total_t else 0
    passed = pct >= CODE_PASS_SCORE
    # Both MCQ and Code must pass to advance
    both_passed = session.get("mcq_passed") and passed
    session.update({"code_score": pct, "code_results": code_results, "code_passed": passed,
                    "screening_stage": 3 if both_passed else 0})
    return redirect(url_for("screening.level2_result"))


@screening_bp.route("/screening/level2/result")
@_login_required
def level2_result():
    # If both MCQ and Code passed, save and redirect to interview
    if session.get("screening_stage") == 3:
        # Save screening result to database
        try:
            user_email = session.get('email')
            user_id = session.get('user_id')
            
            # Fallback: query user if user_id not in session
            if not user_id and user_email:
                user = User.query.filter_by(email=user_email).first()
                if user:
                    user_id = user.id
            
            if user_id:
                mcq_score = session.get("mcq_score")
                code_score = session.get("code_score")
                role = session.get("pending_role", "")
                
                if mcq_score is not None and code_score is not None:
                    result = ScreeningResult(
                        user_id=user_id,
                        email=user_email or "",
                        role=role,
                        mcq_score=mcq_score,
                        code_score=code_score,
                        passed=1
                    )
                    db.session.add(result)
                    db.session.commit()
                    logger.info(f"Saved screening result for user {user_id}: {role} (MCQ: {mcq_score}, Code: {code_score})")
        except Exception as e:
            logger.error(f"Error saving screening result: {e}")
            db.session.rollback()
        
        # Redirect to level3 to start interview
        return redirect(url_for("screening.level3"))
    
    # If didn't pass, show results page
    return render_template("screening/level2_result.html",
                           score=session.get("code_score", 0),
                           passed=session.get("code_passed", False),
                           results=session.get("code_results", []),
                           role=session.get("pending_role", ""),
                           mode=session.get("pending_mode", "chat"))


# ═══════════════════════════════════════════════════════════════════════════════
# LEVEL 3 — Gate → Interview
# ═══════════════════════════════════════════════════════════════════════════════

@screening_bp.route("/screening/level3")
@_login_required
def level3():
    if session.get("screening_stage") != 3:
        return redirect(url_for("home"))

    role = session.pop("pending_role", "Software Engineer")
    mode = session.pop("pending_mode", "chat")
    session.pop("screening_stage", None)
    return redirect(url_for("start", role=role, mode=mode, topic=role))