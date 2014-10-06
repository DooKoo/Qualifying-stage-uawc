from flask import Flask, redirect, request, session, render_template
import requests
import os
import urllib.request
import json

app = Flask(__name__)
encoding = "UTF-8"

key = os.urandom(24)
app.secret_key = key
application_id = "957cf5f9c65fc1e3a92d3a147c75ab20"


class Player:
    def __init__(self, player_name, player_battles, player_wins):
        self.nickname = player_name
        self.battles = player_battles
        self.wins = player_wins


class Tank:
    def __init__(self, tank_owner, tank_id, tank_battles, tank_wins):
        self.owner = tank_owner
        self.id = tank_id
        self.battles = tank_battles
        self.wins = tank_wins


class TankModel:
    def __init__(self, tank_name, tank_id):
        self.name = tank_name
        self.id = tank_id


def parse_neighbors():
    neighbors = {}
    if 'nickname' in session:
        answer = str(urllib.request.urlopen("https://api.worldoftanks.ru/wot/ratings/neighbors/?"
                                            "application_id="+application_id+"&"
                                            "fields=account_id&"
                                            "type=all&"
                                            "account_id="+session['account_id']+"&"
                                            "rank_field=battles_count&"
                                            "limit=10").read(), encoding)
        parse_answer = json.loads(answer)
        if parse_answer['status'] == 'ok':
            data = parse_answer['data']
            for item in data:
                current_id = item['account_id']
                if str(current_id) != session['account_id']:
                    str_answer = str(urllib.request.urlopen("https://api.worldoftanks.ru/wot/account/info/?"
                                                            "application_id="+application_id+"&"
                                                            "account_id="+str(current_id)+"&"
                                                            "fields=nickname,statistics.all.battles,statistics.all.wins").read(), encoding)
                    ready_answer = json.loads(str_answer)
                    if ready_answer['status'] == 'ok':
                        data = ready_answer['data']
                        info = data[str(current_id)]
                        statistics = info['statistics']
                        all_stat = statistics['all']
                        neighbors[current_id] = Player(info['nickname'], all_stat['battles'], all_stat['wins'])
            return neighbors
        else:
            error = parse_answer['error']
            return render_template('error.html', code=error['code'], message=error['message'])
    else:
        return render_template("login.html")


def parse_tanks(neighbors):
    tanks = []
    str_ids = ""

    for item in neighbors.keys():
        str_ids += str(item)+','

    answer = json.loads(str(urllib.request.urlopen("https://api.worldoftanks.ru/wot/account/tanks/?"
                                                   "application_id="+application_id+"&"
                                                   "account_id="+str_ids+"&"
                                                   "fields=tank_id,statistics.battles,statistics.wins").read(), encoding))
    for item in neighbors.keys():
        if answer['status'] == 'ok':
            data = answer['data']
            blocks = data[str(item)]
            for block in blocks:
                stat = block['statistics']
                tanks.append(Tank(item, block['tank_id'], stat['battles'], stat['wins']))

    return tanks


def get_tanks():
    tanks = []
    answer = json.loads(str(urllib.request.urlopen("https://api.worldoftanks.ru/wot/encyclopedia/tanks/?"
                                                   "application_id="+application_id+"&"
                                                   "fields=name,tank_id").read(), encoding))
    if answer['status'] == 'ok':
        data = answer['data']
        for i in data:
            block = data[i]
            tanks.append(TankModel(block['name'], block['tank_id']))
    else:
        error = answer['error']
        return error
    return tanks


@app.route('/')
def main():
    if 'nickname' in session:
        return "<b>Welcome</b> "+session['nickname'] + \
               ". Yo can <a href='http://localhost:5000/logout'>Logout</a> if you want"+"<br>"\
               "Go to <a href='http://localhost:5000/table/battles'>Table</a> of battles<br>"\
               "Go to <a href='http://localhost:5000/table/wins'>Table</a> of wins"
    else:
        return render_template("login.html")


@app.route('/logout')
def out():
    if 'nickname' in session:
        query = "application_id="+application_id+"&access_token="+session['token']
        json_answer = requests.post("https://api.worldoftanks.ru/wot/auth/logout",
                                    data=query)
        answer = json.loads(json_answer.text)

        if answer['status'] == 'ok':
            session.pop('nickname', None)
            session.pop('token', None)
            session.pop('account_id', None)
            session.pop('expires_at', None)
            redirect('http://localhost:5000')
        else:
            error = answer['error']
            return render_template('error.html', code=error['code'], message=error['message'])
    else:
        return render_template("login.html")


@app.route('/auth')
def auth():
    status = request.args.get('status')
    if 'nickname' in session:
        return '<b>'+session['nickname']+'</b> you are logged, go <a href="http://localhost:5000">back</a> to index'
    else:
        if status == 'ok':
            session['nickname'] = request.args.get('nickname')
            session['token'] = request.args.get('access_token')
            session['account_id'] = request.args.get('account_id')
            session['expires_at'] = request.args.get('expires_at')
            return '<b>'+session['nickname']+'</b> you are logged, go <a href="http://localhost:5000">back</a> to index'
        elif status == 'error':
            return render_template('error.html', code=request.args.get('code'), message=request.args.get('message'))
        else:
            answer = json.loads(str(urllib.request.urlopen("https://api.worldoftanks.ru/wot/auth/login/?"
                                                           "application_id="+application_id+"&"
                                                           "nofollow=1&"
                                                           "redirect_uri=http://localhost:5000/auth").read(), encoding))
            if answer['status'] == 'ok':
                data = answer['data']
                return redirect(data['location'])
            else:
                error = answer['error']
                return render_template('error.html', code=error['code'], message=error['message'])


@app.route('/table/<table_type>')
def table(table_type):
    if 'nickname' in session:
        neighbors = parse_neighbors()
        tanks_models = get_tanks()
        tanks = parse_tanks(neighbors)
        answer_str = ""
        if table_type == "battles":
            for model in tanks_models:
                answer_str += "<tr><td>" + model.name+"</td>"
                for neib in neighbors.keys():
                    for tank in tanks:
                        if tank.id == model.id and tank.owner == neib:
                            result = (tank.battles/neighbors[neib].battles)*100
                            answer_str += "<td>" + str(result) + "%</td>"
                answer_str += "</tr>"
            return render_template("table.html", names=neighbors.values(), items=answer_str)
        elif table_type == "wins":
            for model in tanks_models:
                answer_str += model.name+" : "
                rate = 0
                for neib in neighbors.keys():
                    for tank in tanks:
                        if tank.id == model.id and tank.owner == neib:
                            perc = (tank.wins/neighbors[neib].wins)*100
                            rate += perc
                answer_str += str(rate/20) + "%;<br>"
            return answer_str
        else:
            return "Error, please enter correct data! Go <a href='http://localhost:5000'>back</a> to index"
    else:
        return render_template("login.html")

app.run(debug=True, host='0.0.0.0')
