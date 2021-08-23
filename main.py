from flask import Flask, render_template, redirect, url_for, send_file, abort
# create file ignored_file.py with SECRET_KEY, MAIL_USERNAME, MAIL_DEFAULT_SENDER, MAIL_PASSWORD
from ignored_file import SECRET_KEY, MAIL_USERNAME, MAIL_DEFAULT_SENDER, MAIL_PASSWORD
from wtforms import SubmitField, SelectField, StringField
from wtforms.validators import DataRequired, Email
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from bs4 import BeautifulSoup
from flask_apscheduler import APScheduler
from threading import Thread
import requests
import pandas as pd
import re
import os
import glob


app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///emails.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
db = SQLAlchemy(app)
mail = Mail(app)
scheduler = APScheduler()

response = requests.get('https://www.worldometers.info/coronavirus/?utm_campaign=homeAdUOA?Si').text
soup = BeautifulSoup(response, 'lxml')


def covid_19():
    table_covid_th = [th.getText().replace('\n', '').replace('\xa0', '') for th in
                      soup.select('#main_table_countries_today thead tr th')][:15]
    ths = []
    for item in table_covid_th:
        new_item = re.sub(r"(\w)([A-Z])", r"\1 \2", item).replace(',', ', ')
        ths.append(new_item)
    country_name = [tb.getText().replace('\n', '').strip() for tb in
                    soup.select('#main_table_countries_today tbody tr td .mt_a')]
    country_not_a = [tb.getText().replace('\n', '').strip().replace(',', '') for tb in
                     soup.select('#main_table_countries_today tbody tr td span')]
    for item in country_not_a[:]:
        for item in country_not_a[:]:
            if item.isdigit():
                country_not_a.remove(item)
    country_name += country_not_a
    index_country = [str(i) for i in range(1, len(country_name) + 1)]
    table_covid_tb = [tb.getText().replace('\n', '').strip() for tb in
                      soup.select('#main_table_countries_today tbody tr td')]
    country_stat = []
    for i in range(len(table_covid_tb)):
        if table_covid_tb[i] in country_name:
            for i1 in range(14):
                country_stat.append(table_covid_tb[i + i1])
    country_name = [country_stat[i] for i in range(0, len(country_stat), len(ths) - 1)]
    total_cases = [country_stat[i] for i in range(1, len(country_stat), len(ths) - 1)]
    new_cases = [country_stat[i] for i in range(2, len(country_stat), len(ths) - 1)]
    total_deaths = [country_stat[i] for i in range(3, len(country_stat), len(ths) - 1)]
    new_deaths = [country_stat[i] for i in range(4, len(country_stat), len(ths) - 1)]
    total_recovered = [country_stat[i] for i in range(5, len(country_stat), len(ths) - 1)]
    new_recovered = [country_stat[i] for i in range(6, len(country_stat), len(ths) - 1)]
    active_cases = [country_stat[i] for i in range(7, len(country_stat), len(ths) - 1)]
    ser_crit = [country_stat[i] for i in range(8, len(country_stat), len(ths) - 1)]
    tot_cas = [country_stat[i] for i in range(9, len(country_stat), len(ths) - 1)]
    deaths_1m = [country_stat[i] for i in range(10, len(country_stat), len(ths) - 1)]
    total_tests = [country_stat[i] for i in range(11, len(country_stat), len(ths) - 1)]
    tests_1m = [country_stat[i] for i in range(12, len(country_stat), len(ths) - 1)]
    population = [country_stat[i] for i in range(13, len(country_stat), len(ths) - 1)]
    country_stat = [index_country, country_name, total_cases, new_cases, total_deaths, new_deaths, total_recovered,
                    new_recovered, active_cases, ser_crit, tot_cas, deaths_1m, total_tests, tests_1m, population]
    data = {}
    for i in range(len(country_stat)):
        data[ths[i]] = country_stat[i]
    df = pd.DataFrame(data)
    df.to_csv('covid.csv', index=False)
    return data


class SelectCountry(FlaskForm):
    country = SelectField('Country', choices=sorted([value for value in covid_19().values()][1]))
    submit = SubmitField('OK')


class Newsletter(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    country = SelectField('Country', choices=sorted([value for value in covid_19().values()][1]))
    submit = SubmitField('OK')


class Mail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), nullable=False)
    country = db.Column(db.String(250), nullable=False)


db.create_all()


def async_(f):
    def wrapper(*args, **kwargs):
        thr = Thread(target=f, args=args, kwargs=kwargs)
        thr.start()

    return wrapper


def covid_stat():
    cov_num = [number.getText().strip() for number in soup.select('.maincounter-number span')]
    cov_h1 = [number.getText().strip() for number in soup.select('#maincounter-wrap h1')]
    return cov_h1, cov_num


def send_mails():
    all_emails = []
    all_countries = []
    datab = Mail.query.all()
    for i in range(len(datab)):
        all_emails.append(datab[i].email)
        all_countries.append(datab[i].country)
    all_data = covid_19()
    ths = [key for key in all_data.keys()][1:]
    trs = [value for value in all_data.values()]
    names = covid_stat()[0]
    nums = covid_stat()[1]
    for i in range(len(all_emails)):
        msg = Message('Covid-19 Online Statistics', recipients=[all_emails[i]], sender=app.config['MAIL_USERNAME'])
        country_index = trs[1].index(all_countries[i])
        country_trs = [trs[i][country_index] for i in range(len(trs))][1:]
        message = 'World Statistic\n\n'
        for i1 in range(len(names)):
            message += f'{names[i1]} {nums[i1]}\n'
        message += f'\n{all_countries[i]} Statistic\n\n'
        for i2 in range(len(country_trs)):
            message += f'{ths[i2]}: {country_trs[i2]}\n'
        msg.body = message
        async_send_mail(msg)


@async_
def async_send_mail(msg):
    with app.app_context():
        mail.send(msg)


@app.route('/')
def home():
    files_csv = glob.glob('*.csv')
    for file in files_csv:
        os.remove(file)
    names = covid_stat()[0]
    nums = covid_stat()[1]
    return render_template('index.html', names=names, nums=nums, count=len(names))


@app.route('/all-countries')
def all_countries():
    all_data = covid_19()
    ths = [key for key in all_data.keys()]
    trs = [value for value in all_data.values()]
    count_key = len(trs)
    count_val = len(trs[0])
    return render_template('all-countries.html', count_val=count_val, count_key=count_key, trs=trs, ths=ths)


@app.route('/select_country', methods=['GET', 'POST'])
def select_country():
    form = SelectCountry()
    if form.validate_on_submit():
        return redirect(url_for('country', country=form.country.data))
    return render_template('selected_country.html', form=form)


@app.route('/select_country/<country>')
def country(country):
    all_data = covid_19()
    ths = [key for key in all_data.keys()]
    trs = [value for value in all_data.values()]
    country_index = trs[1].index(country)
    country_trs = [trs[i][country_index] for i in range(len(trs))]
    count_key = len(trs)
    data = {}
    for i in range(len(trs)):
        data[ths[i]] = [country_trs[i]]
    df = pd.DataFrame(data, columns=ths)
    df.to_csv(f'{country}.csv', index=False)
    return render_template('country.html', count_key=count_key, ths=ths, trs=country_trs, filename=country)


@app.route('/newsletter', methods=['GET', 'POST'])
def mailing():
    form = Newsletter()
    if form.validate_on_submit():
        email = form.email.data
        countr = form.country.data
        new_email = Mail(email=email, country=countr)
        db.session.add(new_email)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('mail.html', form=form)


@app.route('/all-countries/download_csv/<filename>')
def download_csv(filename):
    try:
        return send_file(f'{filename}.csv', mimetype='csv', attachment_filename=f'{filename}.csv', as_attachment=True)
    except FileNotFoundError:
        abort(404)


if __name__ == '__main__':
    scheduler.add_job(id='send_mails', func=send_mails, trigger='cron', hour=0, minute=0, second=0)
    scheduler.start()
    app.run()
