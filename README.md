# ETL Process for Fetch Data Take-home Assignment

## Introduction
This project demonstrates an ETL (Extract, Transform, Load) process that reads JSON data from an AWS SQS Queue, masks PII (Personally Identifiable Information), and stores the transformed data into a PostgreSQL database.

## Setup Instructions

### Prerequisites
1. **Docker**: Install Docker following the [Docker install guide](https://docs.docker.com/get-docker/).
2. **Docker Compose**: Ensure Docker Compose is installed.
3. **AWS CLI Local**: Install using `pip install awscli-local`.
4. **PostgreSQL**: Install PostgreSQL from the [official website](https://www.postgresql.org/download/).

### Setting up Docker Containers
Use the following Docker images with test data baked in:
- **Postgres**: `fetchdocker/data-takehome-postgres`
- **Localstack**: `fetchdocker/data-takehome-localstack`

Create a `docker-compose.yml` file with the following content:

```yaml
version: "3.9"
services:
  localstack:
    image: fetchdocker/data-takehome-localstack
    ports:
      - "4566:4566"

  postgres:
    image: fetchdocker/data-takehome-postgres
    ports:
      - "5432:5432"
```

Run the Docker containers:
```bash
docker-compose up
```

## Running the Application

1. **Fetch messages from SQS Queue**:
   ```bash
   awslocal sqs receive-message --queue-url http://localhost:4566/000000000000/login-queue
   ```

2. **Connect to PostgreSQL**:
   ```bash
   psql -d postgres -U postgres -p 5432 -h localhost -W
   ```

3. **Run the Python Script**:
   Save the following script as `fetch.py` and run it using:
   ```bash
   python3 fetch.py
   ```

```python
import os
import boto3
import psycopg2
import hashlib
import json

os.environ['AWS_ACCESS_KEY_ID'] = 'dummy'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'dummy'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

def get_sqs_messages():
    sqs = boto3.client('sqs', endpoint_url='http://localhost:4566', region_name='us-east-1')
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
```

## Explanation

### Thought Process and Design Decisions
- **Reading Messages**: Used `boto3` to interact with SQS and fetch messages.
- **Masking PII**: Applied SHA256 hashing to `device_id` and `ip` fields to mask PII while allowing duplicates to be identified.
- **Database Operations**: Utilized `psycopg2` for PostgreSQL interactions, including table creation and data insertion.

### PII Masking
PII fields (`device_id` and `ip`) are hashed using SHA256 to ensure privacy while enabling identification of duplicate values.

## Questions:

1. **How would you deploy this application in production?**:
   - **Containerization**: Using Docker to containerize the application..
   - **CI/CD**: Setting up a continuous integration and continuous deployment (CI/CD) pipeline using tools like Jenkins, GitHub Actions, or GitLab CI.
   - **Orchestration**: Using a container orchestration platform like Kubernetes or Docker Swarm.
   - **Cloud Deployment**: Using a cloud provider such as AWS, GCP, or Azure to deploy and manage the infrastructure.

2. **What other components would you want to add to make this production ready?**:
   - **Logging and Monitoring**: Implement centralized logging (e.g., ELK stack, CloudWatch Logs) and monitoring (e.g., Prometheus, Grafana) to track application performance and errors.
   - **Secrets Management**: Use a secrets management service (e.g., AWS Secrets Manager, HashiCorp Vault) to securely manage database credentials and API keys.
   - **Load Balancing and Auto-scaling**: Use a load balancer to distribute traffic and auto-scaling groups to dynamically adjust the number of running instances based on demand.
   - **Backup and Recovery**: Set up regular backups for the PostgreSQL database and ensure recovery procedures are in place.

3. **How can this application scale with a growing dataset?**:
   - **Database Scaling**: Using a managed database service (e.g., Amazon RDS) that supports vertical and horizontal scaling.
   - **Message Queue Scaling**: Use a scalable message queue service (e.g., AWS SQS) that can handle an increasing number of messages without performance degradation.
   - **Application Scaling**: Deploy the application on a container orchestration platform (e.g., Kubernetes) that supports auto-scaling based on CPU and memory usage.
   - **Batch Processing**: For large datasets, consider batch processing techniques to handle data in chunks, reducing the load on the system.

4. **How can PII be recovered later on?**:
   - **Key Management**: Use a secure key management service (e.g., AWS KMS, Azure Key Vault) to handle encryption and decryption keys.
   - **Audit Logs**: Maintain audit logs for all access to PII data to ensure compliance and traceability.

5. **What are the assumptions you made?**:
   - Necessary environment variables are assumed to be set for AWS and PostgreSQL connections.
   - App version data type was in actual string but it was mentioned Integer in document.
   - Postgres table was not created in actual which too was created with the code.
   - Create_date was not mentioned in the feild message and for that reason it was not considered.


