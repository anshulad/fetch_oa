import os
import boto3
import psycopg2
import hashlib
import json

os.environ['AWS_ACCESS_KEY_ID'] = 'dummy'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'dummy'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


def get_sqs_messages():
    sqs = boto3.client(
        'sqs', endpoint_url='http://localhost:4566', region_name='us-east-1')
    response = sqs.receive_message(
        QueueUrl='http://localhost:4566/000000000000/login-queue',
        MaxNumberOfMessages=10
    )
    return response.get('Messages', [])


def mask_value(value):
    return hashlib.sha256(value.encode()).hexdigest()


def transform_message(message):
    body = json.loads(message['Body'])
    return {
        'user_id': body['user_id'],
        'device_type': body['device_type'],
        'masked_ip': mask_value(body['ip']),
        'masked_device_id': mask_value(body['device_id']),
        'locale': body['locale'],
        'app_version': body['app_version']
    }


def drop_table_if_exists(conn):
    drop_table_query = """
    DROP TABLE IF EXISTS user_logins;
    """
    cur = conn.cursor()
    cur.execute(drop_table_query)
    conn.commit()
    cur.close()


def create_table_if_not_exists(conn):
    create_table_query = """
    CREATE TABLE IF NOT EXISTS user_logins(
        user_id varchar(128),
        device_type varchar(32),
        masked_ip varchar(256),
        masked_device_id varchar(256),
        locale varchar(32),
        app_version varchar(32)
    );
    """
    cur = conn.cursor()
    cur.execute(create_table_query)
    conn.commit()
    cur.close()


def write_to_postgres(records):
    conn = psycopg2.connect(
        dbname='postgres',
        user='postgres',
        password='postgres',
        host='localhost',
        port='5432'
    )
    # drop_table_if_exists(conn)
    create_table_if_not_exists(conn)
    cur = conn.cursor()
    for record in records:
        cur.execute("""
            INSERT INTO user_logins (user_id, device_type, masked_ip, masked_device_id, locale, app_version)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (record['user_id'], record['device_type'], record['masked_ip'], record['masked_device_id'], record['locale'], record['app_version']))
    conn.commit()
    cur.close()
    conn.close()


def fetch_and_display_records(conn):
    fetch_query = "SELECT * FROM user_logins;"
    cur = conn.cursor()
    cur.execute(fetch_query)
    rows = cur.fetchall()
    for row in rows:
        print(row)
    cur.close()


if __name__ == '__main__':
    conn = psycopg2.connect(
        dbname='postgres',
        user='postgres',
        password='postgres',
        host='localhost',
        port='5432'
    )
    messages = get_sqs_messages()

    for msg in messages:
        print(msg)

    if messages:
        records = [transform_message(msg) for msg in messages]
        write_to_postgres(records)
    print(fetch_and_display_records(conn))
