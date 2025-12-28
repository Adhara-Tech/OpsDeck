# OpsDeck Data Import Guide

OpsDeck provides a command-line interface (CLI) to bulk import data via CSV files. This is useful for initial system bootstrapping or migrating from legacy tools.

## General Usage

All commands are executed via the Flask CLI.
If you are running OpsDeck via Docker (recommended), you must execute these commands inside the container.

**Example using Docker:**
1. Copy your CSV file into the container:
   ```bash
   docker cp my_data.csv opsdeck_web_1:/app/

```

2. Run the import command:
```bash
docker exec -it opsdeck_web_1 flask data-import [COMMAND] my_data.csv

```



---

## 1. Import Users

Imports users into the system.

* **Security Note:** All imported users are assigned the `user` role by default.
* **Passwords:** Secure random passwords are automatically generated and displayed in the console output.

### Command

```bash
flask data-import users <filename.csv>

```

### CSV Format

| Header | Required | Description |
| --- | --- | --- |
| `name` | Yes | Full name of the user. |
| `email` | Yes | User email (must be unique). |

**Example `users.csv`**

```csv
name,email
Alice Johnson,alice@example.com
Bob Smith,bob@example.com

```

---

## 2. Import Suppliers

Imports vendors/suppliers into the database. Duplicate names will be skipped.

### Command

```bash
flask data-import suppliers <filename.csv>

```

### CSV Format

| Header | Required | Description |
| --- | --- | --- |
| `name` | Yes | Company name. |
| `email` | No | General contact email. |
| `phone` | No | General contact phone. |
| `address` | No | Physical address. |
| `compliance_status` | No | e.g., `Approved`, `Pending`, `Rejected`. Defaults to `Pending`. |

**Example `suppliers.csv`**

```csv
name,email,phone,compliance_status
Acme Corp,contact@acme.com,555-0199,Approved
Tech Supplies Inc,sales@techsupplies.com,,Pending

```

---

## 3. Import Contacts

Imports specific people associated with a Supplier.

* **Auto-Link:** OpsDeck will look up the `supplier_name` in the database.
* **Auto-Create:** If the supplier does not exist, it will be created automatically.

### Command

```bash
flask data-import contacts <filename.csv>

```

### CSV Format

| Header | Required | Description |
| --- | --- | --- |
| `name` | Yes | Contact person's name. |
| `supplier_name` | Yes | Must match the supplier's name exactly. |
| `email` | No | Contact email. |
| `phone` | No | Contact phone number. |
| `role` | No | Job title (e.g., Account Manager). |

**Example `contacts.csv`**

```csv
name,supplier_name,email,role
John Doe,Acme Corp,john.doe@acme.com,Account Manager
Jane Smith,Tech Supplies Inc,jane@techsupplies.com,Support Lead

```

---

## 4. Import Assets

Imports IT assets (laptops, servers, etc.).

* **Locations:** If `location_name` does not exist, it will be created automatically.
* **Dates:** Format must be `YYYY-MM-DD`.

### Command

```bash
flask data-import assets <filename.csv>

```

### CSV Format

| Header | Required | Description |
| --- | --- | --- |
| `name` | Yes | Asset name (e.g., "MacBook Pro 16"). |
| `model` | No | Specific model identifier. |
| `brand` | No | Manufacturer (e.g., Apple, Dell). |
| `serial_number` | No | Unique serial number. |
| `location_name` | No | Where the asset is located. |
| `status` | No | e.g., `In Use`, `In Stock`, `Repair`. Defaults to `In Use`. |
| `cost` | No | Purchase cost (numeric). |
| `purchase_date` | No | Format: `YYYY-MM-DD`. |
| `warranty_length` | No | Warranty duration in months (integer). |

**Example `assets.csv`**

```csv
name,model,brand,serial_number,location_name,status,cost,purchase_date,warranty_length
MBP-DEV-01,MacBook Pro,Apple,C02XYZ123,HQ Office,In Use,2499.00,2023-01-15,24
Dell-Server-01,PowerEdge,Dell,SERV888,Server Room A,In Stock,4500.00,2022-11-20,36

```

---

## 5. Import Peripherals

Imports accessories (monitors, keyboards, docks).

### Command

```bash
flask data-import peripherals <filename.csv>

```

### CSV Format

| Header | Required | Description |
| --- | --- | --- |
| `name` | Yes | Device name (e.g., "Dell Monitor 24"). |
| `type` | No | e.g., `Monitor`, `Keyboard`, `Mouse`. Defaults to `Accessory`. |
| `brand` | No | Manufacturer. |
| `serial_number` | No | Unique serial number. |
| `status` | No | Defaults to `In Use`. |

**Example `peripherals.csv`**

```csv
name,type,brand,serial_number,status
Dell UltraSharp 27,Monitor,Dell,CN-0X123,In Use
Logitech MX Master 3,Mouse,Logitech,SN998877,In Use

```