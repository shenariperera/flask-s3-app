
from flask import Flask, render_template, request
import key_config as keys
import boto3 
import dynamoDB_create_table as dynamodb_ct
from boto3.dynamodb.conditions import Key, Attr
from operator import itemgetter
import urllib.parse

app = Flask(__name__)


dynamodb = boto3.resource(
    'dynamodb',
    #aws_access_key_id     = keys.ACCESS_KEY_ID,
    #aws_secret_access_key = keys.ACCESS_SECRET_KEY,
    region_name           = keys.REGION_NAME,
)

s3 = boto3.resource(
    's3',
    #aws_access_key_id     = keys.ACCESS_KEY_ID,
    #aws_secret_access_key = keys.ACCESS_SECRET_KEY,
    region_name           = keys.REGION_NAME,
)



@app.route('/')
def index():
    #dynamodb.create_table_reg_users()
    #return 'Table Created'
    table = dynamodb.Table('reg_users')

    response = table.scan(ProjectionExpression='email, reg_number, #n', ExpressionAttributeNames={'#n': 'name'})

    if 'Items' in response:
        users = response['Items']
        sorted_users = sorted(users, key=itemgetter('reg_number'))  # Sort the users by reg_number
        return render_template('index.html', users=sorted_users)

    return 'No users found'
    

@app.route('/login')
def login():
    return render_template('login.html')

# function to generate registration number
def generate_registration_number():
    table = dynamodb.Table('reg_users')
    response = table.scan()
    items = response['Items']
    if items:
        last_registration_number = max(int(item['reg_number']) for item in items)
        return str(last_registration_number + 1)
    else:
        return '1000'  # Initial registration number

        
@app.route('/signup')
def signup():
    reg_no = generate_registration_number()
    return render_template('signup.html', reg_no=reg_no)

@app.route('/edit')
def edit():
    return render_template('edit.html')
    

#to create accounts
@app.route('/signup-action', methods=['post'])
def signupAction():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        degree_program = request.form['degree_program']
        contact = request.form['contact']
        gpa = request.form['gpa']
        skills = request.form['skills']
        introduction = request.form['introduction']
        reg_number = request.form['reg_number']
        
        file = request.files['image']
        filename = file.filename
        bucket_name = 'flask-s3-app'
        bucket = s3.Bucket(bucket_name)
        bucket.put_object(
            Key=filename,
            Body=file,
            ContentType='image/jpeg',
            ContentDisposition='inline'
        )
    
        encoded_object_key = urllib.parse.quote(filename)
        object_url = f"https://{bucket_name}.s3.amazonaws.com/{encoded_object_key}"
        
        
        table = dynamodb.Table('reg_users')
        
        table.put_item(
                Item={
        'reg_number' : reg_number,
        'name': name,
        'email': email,
        'password': password,
        'degree_program' : degree_program,
        'contact' : contact,
        'gpa' : gpa,
        'skills' : skills,
        'introduction' : introduction,
        'image' : object_url,
            }
        )
        msg = "Registration Complete. Please Login to your account !"
    
        return render_template('login.html',msg = msg)
    return render_template('signup.html')


#to pass data to edit page 
@app.route('/edit',methods = ['post'])
def check():
    if request.method=='POST':
        
        email = request.form['email']
        password = request.form['password']
        
        table = dynamodb.Table('reg_users')
        response = table.query(
                KeyConditionExpression=Key('email').eq(email)
        )
        items = response['Items']
        reg_number = items[0]['reg_number']
        email = items[0]['email']
        name = items[0]['name']
        contact = items[0]['contact']
        degree_program = items[0]['degree_program']
        gpa = items[0]['gpa']
        skills = items[0]['skills']
        introduction = items[0]['introduction']
        
        print(items[0]['password'])
        
        if password == items[0]['password']:
            
            return render_template("edit.html",reg_number = reg_number, email = email, name = name, contact = contact, degree_program = degree_program, gpa = gpa, skills = skills, introduction = introduction)
    return render_template("login.html")


#to update profiles
@app.route('/edit-profile/<string:email>', methods=['PUT'])
def editProfile(email):
    data = request.get_json()
    table = dynamodb.Table('reg_users')

    response = table.update_item(
        Key={
            'email': email
        },
        UpdateExpression='SET #n = :name, #c = :contact, #dp = :degree_program, #gpa = :gpa, #s = :skills, #i = :introduction',
        ExpressionAttributeNames={
            '#n': 'name',
            '#c': 'contact',
            '#dp': 'degree_program',
            '#gpa': 'gpa',
            '#s': 'skills',
            '#i': 'introduction'
        },
        ExpressionAttributeValues={
            ':name': data['name'],
            ':contact': data['contact'],
            ':degree_program': data['degree_program'],
            ':gpa': data['gpa'],
            ':skills': data['skills'],
            ':introduction': data['introduction']
        },
        ReturnValues='ALL_NEW'  
    )
    
    if (response['ResponseMetadata']['HTTPStatusCode'] == 200):
        return {
            'msg': 'Updated successfully',
            'ModifiedAttributes': response.get('Attributes'),
            'response': response['ResponseMetadata']
        }

    return {
        'msg': 'Some error occurred',
        'response': response
    }
    

#to create profile view paths
@app.route('/profile/<string:reg_number>')
def viewProfile(reg_number):
    table = dynamodb.Table('reg_users')

    response = table.scan(
        FilterExpression=Attr('reg_number').eq(reg_number)
    )

    if 'Items' in response and len(response['Items']) > 0:
        user = response['Items'][0]
        return render_template('profile-view.html', user=user)

    return 'User not found'


if __name__ == '__main__':
    app.run(debug=True,port=8080,host='0.0.0.0')