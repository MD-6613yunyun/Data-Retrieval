# importing the required modules
import xmlrpc.client
import time
from datetime import date, timedelta


class LineTracker:
    BI_tracker = {}
    ID_create = {}

    def __init__(self, db, username, pwd):
        self.db = db
        self.username = username
        self.pwd = pwd
        self.uid = 0
        self.total_record_creations = 0

    def authenticate_server(self, server):
        common = xmlrpc.client.ServerProxy("{}/xmlrpc/2/common".format(server))
        uid = common.authenticate(self.db, self.username, self.pwd, {})
        if uid:
            print(f"Authenticated with the unique ID - {uid}")
            self.uid = uid
        else:
            print("Invalid credentials or login..")
            print("Try again with valid credentials")
        return uid

    def initialize_objects_in_server(self, server: str):
        models = xmlrpc.client.ServerProxy("{}/xmlrpc/2/object".format(server))
        return models

    def track_lines(self, obj_models: object, model: str):
        domain = [('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date)]
        results = obj_models.execute_kw(self.db, self.uid, self.pwd, model, 'search_read',
                                        [domain], {"fields": ['id', 'unit_id', 'create_uid']})
        for data in results:
            if data['create_uid'][0] not in self.ID_create:
                self.ID_create[data['create_uid'][0]] = 1
            else:
                self.ID_create[data['create_uid'][0]] += 1
            unit = data['unit_id'][1]
            if unit not in self.BI_tracker:
                self.BI_tracker[unit] = 1
            else:
                self.BI_tracker[unit] += 1
        self.total_record_creations += len(results)
        return len(results)

    def track_lines_for_accountant(self, obj_models: object):
        domain = [
            [('cash_type', '=', 'pay'), ('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date)],
            [('cash_type', '=', 'receive'), ('create_date', '>=', self.start_date),
             ('create_date', '<=', self.end_date)],
            [('partner_type', '=', 'supplier'), ('payment_type', '=', 'inbound'),
             ('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date)],
            [('partner_type', '=', 'supplier'), ('payment_type', '=', 'outbound'),
             ('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date)],
            [('partner_type', '=', 'customer'), ('payment_type', '=', 'inbound'),
             ('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date)],
            [('partner_type', '=', 'customer'), ('payment_type', '=', 'outbound'),
             ('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date)]]
        acc_results = []
        for i in range(6):
            if 0 <= i < 2:
                model = 'account.cashbook'
                name = 'tree_unit'
            else:
                model = 'account.payment'
                name = 'unit_id'
            results = obj_models.execute_kw(self.db, self.uid, self.pwd, model, 'search_read',
                                            [domain[i]], {"fields": ['id', name, 'create_uid']})
            for data in results:
                if data['create_uid'][0] not in self.ID_create:
                    self.ID_create[data['create_uid'][0]] = 1
                else:
                    self.ID_create[data['create_uid'][0]] += 1
                unit = data[name][1] if 'unit_id' in data else data[name]
                if unit not in self.BI_tracker:
                    self.BI_tracker[unit] = 1
                else:
                    self.BI_tracker[unit] += 1
            acc_results.append(len(results))
        self.total_record_creations += sum(acc_results)
        return acc_results

    def department_counts(self, obj_models: object):
        results = obj_models.execute_kw(self.db, self.uid, self.pwd, 'res.users', 'read',
                                        [list(self.ID_create.keys())], {"fields": ['department_id']})
        depart_count = {}
        for i, (key, value) in enumerate(self.ID_create.items()):
            if results[i]['department_id'][1] not in depart_count:
                depart_count[results[i]['department_id'][1]] = value
            else:
                depart_count[results[i]['department_id'][1]] += value
        return depart_count

    def set_date(self, month, day, year, auto=True):
        if auto:
            self.end_date = date.today().strftime('%Y-%m-%d') + " 17:29:59"
            self.start_date = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d') + " 17:30:13"
        else:
            self.start_date = f"{str(year)}-0{str(month)}-{str(day - 1)} 17:30:13"
            self.end_date = f"{str(year)}-0{str(month)}-{str(day)} 17:29:59"


if __name__ == "__main__":
    # time initialization to determine the program's execution time
    start = time.time()
    # server and database declaration
    server, db = "http://ec2-18-139-153-219.ap-southeast-1.compute.amazonaws.com", "mmm_uat"
    # username and password
    username, pwd = "MD-6613", "MD-6613"
    #  models used to check in
    models_check_in = ["sale.order", 'purchase.order', 'purchase.requisition', 'stock.inventory.adjustment',
                       'expense.prepaid','hr.expense', 'duty.process.line']
    # naming conventions for models
    model_names = ["Sales Module , ", "Purchase Module , ", "Inventroy Requisition Module , ",
                   "Inventory Adjustment Module , ",
                   "Advance Expenses Module , ", "General Expense Module , ", "Duty Process Module , "]
    ## Data processing
    # create an instance of our line tracker object
    mmm = LineTracker(db, username, pwd)
    # authentication
    uid = mmm.authenticate_server(server)
    # objects intialization to process datas within models
    models_obj = mmm.initialize_objects_in_server(server)
    # setting up the date when records were created
    mmm.set_date(3, 27, 2023)
    ## csv file creation and getting the data
    file_path = "C:\MDMM\Projects\Scripts\Tracker for  server line creation\modules.txt"
    with open(file_path, "w") as file:
        # Declaration of authentication with the UID
        file.write(f"Authenticated with the unique ID - {mmm.uid}" + "\n")
        # looping through the declared model and process the retrieval
        for i in range(6):
            # write the result and model name to the file
            file.write(model_names[i] + str(mmm.track_lines(models_obj, models_check_in[i])) + "\n")
        # account modules name to be checked in
        modules_accountant = ['Cashbook Payment Module', 'Cashbook Receipt Module', 'Vendor Receipt Module',
                              'Vendor Payment Module', 'Customer Receipt Module', 'Customer Payment Module']
        # data retrival from account module
        account = mmm.track_lines_for_accountant(models_obj)  # account
        # looping through the results and writing the results
        for i in range(6):
            file.write(modules_accountant[i] + " , " + str(account[i]) + "\n")
        # writing through the Business Unit counts to the file
        for key, value in mmm.BI_tracker.items():
            file.write(f"{key} , {value} \n")
        # data retrieval for department counts
        department_counts = mmm.department_counts(models_obj)
        # writing through the Department Counts to the file
        for key, value in department_counts.items():
            file.write(f"{key} Department , {value} \n")
        # writing total record creations
        file.write(f"Total record creations {date.today()} => {mmm.total_record_creations} \n")
        end_time = time.time()
        file.write(f"Automation program executed in {end_time - start} s ")