from flask import Flask, render_template, jsonify, request, session
import random
import json

app = Flask(__name__)
app.secret_key = 'assessment-sim-secret-2024'


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/game/bart')
def bart():
    return render_template('bart.html')


@app.route('/game/gonogo')
def gonogo():
    return render_template('gonogo.html')


@app.route('/game/digit-span')
def digit_span():
    return render_template('digit_span.html')


@app.route('/game/nback')
def nback():
    return render_template('nback.html')


@app.route('/game/numerical')
def numerical():
    return render_template('numerical.html')


@app.route('/game/verbal')
def verbal():
    return render_template('verbal.html')


@app.route('/game/inductive')
def inductive():
    return render_template('inductive.html')


@app.route('/game/sjt')
def sjt():
    return render_template('sjt.html')


@app.route('/game/attention')
def attention():
    return render_template('attention.html')


@app.route('/results')
def results():
    score_data = request.args.get('data', '{}')
    return render_template('results.html', score_data=score_data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
