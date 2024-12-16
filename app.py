from datetime import datetime, timedelta
from functools import wraps
from sqlalchemy.sql import func
from flask import request, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
import jwt

from .model import Users, Funds


from . import app
from . import db


# decorator for verifying the JWT
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # jwt is passed in the rquest headers as Authorization
        if 'Authorization' in request.headers:
            token = request.headers['Authorization']
            print(token)
        
        # return 401 if token is not passed
        if not token:
            return jsonify({"message": "Token is missing"}), 401
        
        try: 
            data = jwt.decode(token, "secret",algorithms=["HS256"])
            current_user = Users.query.filter_by(id = data["id"]).first()
            print(current_user)
        except Exception as e:
            print(e)
            return jsonify({
                "message": "Token is invalid"
            }), 401
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/login', methods = ['POST'])
def login():
    auth = request.json

    # 401 not authorized, 
    # status code indicates that the request has not been applied because it lacks 
    # valid authentication credentials for the target resource
    if not auth or not auth.get('email') or not auth.get('password'):
        return make_response(
            'Proper Credentials not provided',
            401
        )
    user = Users.query.filter_by(email = auth.get('email')).first()
    if not user:
        return make_response(
            'Please create an account',
            401
        )
    
    if check_password_hash(user.password, auth.get('password')):
        token = jwt.encode({
            'id': user.id,
            'exp': datetime.utcnow() + timedelta(minutes= 30)
        }, "secret", "HS256")
        return make_response(jsonify({'token': token}), 201)
    #  password is wrong
    return make_response(
        'Please check your credentails',
        401
    )
@app.route("/signup", methods=['POST'])
def signup():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    firstName = data.get('firstName')
    lastName = data.get('lastName')
    if firstName and lastName and email and password:
        user = Users.query.filter_by(email = email ).first()
        if user: 
            return make_response(
                {"message": 'Please Sign In'},
                200 # Already have an account, not a server error. You can use 409 depends on design
            )
        user = Users(
            email = data['email'], 
            password =  generate_password_hash(data['password']),
            firstName= data['firstName'],
            lastName= data['lastName']
        )
        db.session.add(user)
        db.session.commit()
        return make_response(
             {"message": 'User Created'},
                201 
            )
    return make_response(
            {"message":  'Unable to create User'},
            500 
    )


@app.route("/funds", methods=['GET'])
@token_required
def getAllFunds(current):
    funds = Funds.query.filter_by(userId=current.id).all()
    totalSum = 0
    if funds:
         totalSum = Funds.query.with_entities(db.func.round(func.sum(Funds.amount), 2)).filter_by(userId = current.id).all()[0][0]
       
    return jsonify({
        "data":[ row.serialize for row in funds ],
        "sum": totalSum
    })


@app.route("/funds/<id>", methods=['PUT'])
@token_required
def updateFund(current, id):
    try:
        funds = Funds.query.filter_by(userId=current.id, id=id).first()
        if funds == None:
            return {"message":"Unable to update"}, 409
        data = request.json
        if data["amount"]:
            funds.amount = data["amount"]
            
        db.session.commit()
       
        return {"message":funds.serialize}, 200
    except Exception as e:
        print(e)
        return {"error":"Unable to process"}, 409

@app.route("/funds", methods=['POST'])
@token_required
def postFund(current):
    data = request.json
    if data["amount"]:
        fund = Funds(
            amount=data["amount"],
            userId=current.id
        )
        db.session.add(fund)
        db.session.commit()
        print(fund)
    return fund.serialize

@app.route("/funds/<id>", methods=['DELETE'])
@token_required
def deleteFund(current, id):
    try:
        funds = Funds.query.filter_by(userId=current.id, id=id).first()
        if funds == None:
            return {"message":f"Fund with {id} not found"}, 404
        db.session.delete(funds)
        db.session.commit()
       
        return {"message":"Deleted"}, 202
    except Exception as e:
        print(e)
        return {"error":"Unable to process"}, 409


