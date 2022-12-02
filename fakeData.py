import faker
import random
from faker.providers import bank, credit_card, geo, address, person, company
import psycopg2
from argon2 import PasswordHasher
import string
import threading

fakerObj = faker.Faker()
fakerObj.add_provider(bank)
fakerObj.add_provider(credit_card)
fakerObj.add_provider(geo)
fakerObj.add_provider(address)
fakerObj.add_provider(person)
fakerObj.add_provider(company)

db_connection = psycopg2.connect(
    database="rna", user="minor", password="dev", host="localhost", port=5432)

db_connection.set_session(autocommit=True)
db_cursor = db_connection.cursor()


def create_branch_details():
    ifsc = random.randint(100000, 999999)
    name = fakerObj.company()
    addr = fakerObj.address()
    obj = {'branch_id': ifsc, 'branch_name': name, 'branch_address': addr}
    return obj


def create_customer():
    f = open('cust_details.txt', 'a+')
    customer_id = random.randint(1000000000, 9999999999)
    account_no = fakerObj.bban()
    full_name = f"{fakerObj.first_name()} {fakerObj.last_name()}"
    balance = random.randint(0, 100000)
    ac_type = random.randint(0, 2)
    password_plain = ''.join(
        [random.choice(string.ascii_letters + string.digits) for _ in range(6)])
    ph = PasswordHasher()
    password_hash = ph.hash(password_plain)
    record = f"{customer_id}:{password_plain} - {full_name}\n"
    f.write(record)
    branch = random.choice(branches)['branch_id']
    obj = {'customer_id': customer_id, 'account_no': account_no,
           'full_name': full_name, 'balance': balance, 'ac_type': ac_type, 'home_branch': branch, 'password': password_hash}
    # print(obj)
    f.close()
    return obj


def create_cards(customers: list):
    if len(customers) == 0:
        return
    while len(customers) > 0:
        card_no = fakerObj.credit_card_number()
        card_type = random.randint(0, 1)
        pin = random.randint(0000, 9999)
        cvv = fakerObj.credit_card_security_code()
        exp_date = fakerObj.credit_card_expire(date_format="%Y/%m/%d")
        txn_limit = None
        credit_limit = None
        if card_type == 1:
            credit_limit = random.randint(0, 300000)
        else:
            txn_limit = random.randint(0, 100000)
        ac_no_c = random.choice(customers)
        customers.remove(ac_no_c)
        ac_no = ac_no_c['account_no']

        obj = {
            'card_no': card_no,
            'card_type': card_type,
            'pin': pin,
            'cvv': cvv,
            'exp_date': exp_date,
            'txn_limit': txn_limit,
            'credit_limit': credit_limit,
            'ac_no': ac_no
        }

        cards.append(obj)


def create_atms(branches: list):
    if len(branches) == 0:
        return
    while len(branches) > 0:
        atm_id = random.randint(10000000, 99999999)
        atm_address = fakerObj.address()
        atm_branch_c = random.choice(branches)
        atm_branch = atm_branch_c['branch_id']
        branches.remove(atm_branch_c)
        location = list(fakerObj.local_latlng(
            country_code="IN", coords_only=True))
        location = [float(i) for i in location]
        location = parse_array_to_psql(tuple(location))
        balance = random.randint(0, 9999999)

        obj = {'atm_id': atm_id, 'atm_address': atm_address,
               'branch': atm_branch, 'location': location, 'balance': balance}
        atms.append(obj)


def parse_array_to_psql(arr):
    arr_stmt = "{"
    for a in arr:
        arr_stmt += str(a) + ", "
    arr_stmt = arr_stmt[:len(arr_stmt) - 2]
    arr_stmt += "}"
    return arr_stmt


def prepare_insert_sql(data: dict, tbl_name: str = "tbl"):
    stmt = f'INSERT INTO {tbl_name}('
    for col in data.keys():
        stmt += str(col) + ','
    stmt = stmt[:len(stmt) - 1]
    stmt += ') VALUES ('
    for _ in data.values():
        if (tbl_name == "atm" and type(_) == type(tuple([]))):
            stmt += '%s::double precision[], '
            continue
        stmt += '%s, '
    stmt = stmt[:len(stmt)-2]
    stmt += ')'
    return (stmt, tuple(data.values()))

branches = []
atms = []
customers = []
cards = []
for _ in range(30):
    branches.append(create_branch_details())

for branch in branches:
    stmt_dt = prepare_insert_sql(branch, 'branch')
    db_cursor.execute(stmt_dt[0], stmt_dt[1])
print("Branches Done")

create_atms(list(branches))
for atm in atms:
    stmt_dt = prepare_insert_sql(atm, 'atm')
    db_cursor.execute(stmt_dt[0], stmt_dt[1])
print("ATMs Done")

def main(start=0, end=1000):
    global cards
    global customers
    cards = []
    customer = []   
    for _ in range(start, end+1):
        customers.append(create_customer())
        print(f"{_} record inserted")

    for customer in customers:
        stmt_dt = prepare_insert_sql(customer, 'customer')
        db_cursor.execute(stmt_dt[0], stmt_dt[1])
    print(f"Customers {start} to {end} Done")

    create_cards(list(customers))
    for card in cards:
        stmt_dt = prepare_insert_sql(card, 'card')
        db_cursor.execute(stmt_dt[0], stmt_dt[1])
    print(f"Cards {start} to {end} - Done")

    db_connection.commit()
    db_connection.close()


threading.Thread(target=main, args=(0,99)).start()
# for i in range(10):
#     print(f"{i+1}th Thread Created")
#     threading.Thread(target=main, args=(i*1000,i*1000 + 1000)).start()
