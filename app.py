"""Flask application for AssessSim — internship assessment game simulator."""
from flask import Flask, render_template, request

app = Flask(__name__)
app.secret_key = 'assessment-sim-secret-2024'


@app.route('/')
def index():
    """Render the home page."""
    return render_template('index.html')


@app.route('/game/bart')
def bart():
    """Render the BART balloon risk game."""
    return render_template('bart.html')


@app.route('/game/gonogo')
def gonogo():
    """Render the Go/No-Go impulse control game."""
    return render_template('gonogo.html')


@app.route('/game/digit-span')
def digit_span():
    """Render the digit span working memory game."""
    return render_template('digit_span.html')


@app.route('/game/nback')
def nback():
    """Render the N-Back fluid intelligence game."""
    return render_template('nback.html')


@app.route('/game/numerical')
def numerical():
    """Render the SHL numerical reasoning test."""
    return render_template('numerical.html')


@app.route('/game/verbal')
def verbal():
    """Render the SHL verbal reasoning test."""
    return render_template('verbal.html')


@app.route('/game/inductive')
def inductive():
    """Render the SHL inductive reasoning test."""
    return render_template('inductive.html')


@app.route('/game/sjt')
def sjt():
    """Render the Cappfinity situational judgment test."""
    return render_template('sjt.html')


@app.route('/game/attention')
def attention():
    """Render the attention and focus game."""
    return render_template('attention.html')


@app.route('/results')
def results():
    """Render the results page with score data from query params."""
    score_data = request.args.get('data', '{}')
    return render_template('results.html', score_data=score_data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
