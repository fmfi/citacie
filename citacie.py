from flask import Flask
app = Flask(__name__)

from flask import render_template

@app.route('/')
def index():
  return render_template('index.html')

if __name__ == '__main__':
  import os
  if 'CITACIE_DEBUG' in os.environ:
    app.debug = True
  app.run()