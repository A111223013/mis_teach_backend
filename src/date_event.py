from flask import Flask, request, jsonify ,Blueprint
from flask_sqlalchemy import SQLAlchemy
import redis, json ,time
from datetime import datetime

date_bp = Blueprint('date_event',__name__)
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://username:password@localhost:3306/db_name'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
r = redis.Redis(host='localhost', port=6379, db=0)



class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String)
    title = db.Column(db.String)
    start = db.Column(db.DateTime)
    end = db.Column(db.DateTime, nullable=True)
    notify = db.Column(db.Boolean, default=False)
    notify_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String, default='active')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'start': self.start.isoformat(),
            'notify': self.notify,
            'notify_time': self.notify_time.isoformat() if self.notify_time else None
        }

@date_bp.route('/api/events', methods=['GET', 'POST'])
def events():
    if request.method == 'GET':
        all_events = Event.query.all()
        return jsonify([{
            'id': e.id,
            'title': e.title,
            'start': e.start.isoformat(),
            'end': e.end.isoformat() if e.end else None,
            'notify': e.notify,
            'notify_time': e.notify_time.isoformat() if e.notify_time else None,
            'status': e.status,
            'user_id': e.user_id
        } for e in all_events])

    data = request.json
    new_event = Event(
        user_id=data['user_id'],
        title=data['title'],
        start=datetime.fromisoformat(data['start']),
        end=datetime.fromisoformat(data['end']) if data.get('end') else None,
        notify=data.get('notify', False),
        notify_time=datetime.fromisoformat(data['notify_time']) if data.get('notify_time') else None
    )
    db.session.add(new_event)
    db.session.commit()

    if new_event.notify and new_event.notify_time:  
        r.set(f"notify:{new_event.id}", json.dumps({
            'title': new_event.title,
            'user_id': new_event.user_id,
            'notify_time': new_event.notify_time.isoformat()
        }))

    return jsonify({'id': new_event.id}), 201

@date_bp.route('/api/events/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    event = Event.query.get(event_id)
    if event:
        db.session.delete(event)
        db.session.commit()
        r.delete(f"notify:{event_id}")
        return '', 204
    return 'Not found', 404

#Python 背景程式監控 Redis
while True:
    for key in r.keys("notify:*"):
        data = json.loads(r.get(key))
        notify_time = datetime.fromisoformat(data['notify_time'])
        if datetime.now() >= notify_time:
            print(f"通知給使用者 {data['user_id']} 事件: {data['title']}")
            # TODO: email / LINE
            r.delete(key)
    time.sleep(60)