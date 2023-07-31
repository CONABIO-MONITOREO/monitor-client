from flask import Blueprint, render_template, request, flash
from werkzeug.utils import secure_filename
import os

form = Blueprint('form', __name__)

@form.route('/form', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        text1 = request.form['text1']
        text2 = request.form['text2']
        text3 = request.form['text3']
        print(text3)
        directories = request.form.getlist('directory')
        # Do something with the form data and directories here

        flash('Form submission successful')
        return render_template('form.html')
    return render_template('form.html')

