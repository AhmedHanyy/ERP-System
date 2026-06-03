from app import db
from datetime import datetime
import os

# Check if we should use database schemas (PostgreSQL supports schemas, SQLite does not)
DATABASE_URL = os.environ.get('DATABASE_URL', '')
IS_POSTGRES = DATABASE_URL.startswith('postgresql') or DATABASE_URL.startswith('postgres')
SCHEMA_NAME = 'warehouse'

class WarehouseModel:
    """Base class configuration helper for warehouse tables."""
    @classmethod
    def get_table_args(cls, table_name):
        if IS_POSTGRES:
            return {'schema': SCHEMA_NAME}
        return {}

# ─── DIMENSIONS ───────────────────────────────────────────────────────────────

class DimCustomer(db.Model):
    """
    Customer Dimension.
    """
    __tablename__ = 'dim_customer'
    __table_args__ = WarehouseModel.get_table_args('dim_customer')

    CustomerKey        = db.Column(db.Integer, primary_key=True)
    ShopifyCustomerID  = db.Column(db.String(100), unique=True, nullable=True)
    FirstName          = db.Column(db.String(100), nullable=True)
    LastName           = db.Column(db.String(100), nullable=True)
    Email              = db.Column(db.String(150), nullable=True, index=True)
    Phone              = db.Column(db.String(50), nullable=True)
    City               = db.Column(db.String(100), nullable=True)
    Region             = db.Column(db.String(100), nullable=True) # Normalized Governorate
    Country            = db.Column(db.String(100), nullable=True)
    AcceptsMarketing   = db.Column(db.Boolean, default=False)
    RFM_Segment        = db.Column(db.String(50), nullable=True)
    created_at         = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'CustomerKey': self.CustomerKey,
            'ShopifyCustomerID': self.ShopifyCustomerID,
            'FirstName': self.FirstName,
            'LastName': self.LastName,
            'Email': self.Email,
            'Phone': self.Phone,
            'City': self.City,
            'Region': self.Region,
            'Country': self.Country,
            'AcceptsMarketing': self.AcceptsMarketing,
            'RFM_Segment': self.RFM_Segment,
        }


class DimProduct(db.Model):
    """
    Product Dimension (Supports SCD Type 2).
    """
    __tablename__ = 'dim_product'
    __table_args__ = WarehouseModel.get_table_args('dim_product')

    ProductKey    = db.Column(db.Integer, primary_key=True)
    SKU           = db.Column(db.String(100), nullable=False) # Business key (not unique in table due to SCD 2)
    Handle        = db.Column(db.String(200), nullable=True)
    Title         = db.Column(db.String(200), nullable=False)
    Category      = db.Column(db.String(150), nullable=True)
    Size          = db.Column(db.String(50), nullable=True)
    Color         = db.Column(db.String(50), nullable=True)
    Price         = db.Column(db.Float, nullable=False)
    Cost          = db.Column(db.Float, nullable=False)
    Vendor        = db.Column(db.String(100), nullable=True)
    Status        = db.Column(db.String(50), default='active')
    IsActive      = db.Column(db.Boolean, default=True)
    
    # SCD Type 2 Fields
    RowStartDate  = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    RowEndDate    = db.Column(db.DateTime, nullable=True)
    IsCurrent     = db.Column(db.Boolean, nullable=False, default=True, index=True)

    def to_dict(self):
        return {
            'ProductKey': self.ProductKey,
            'SKU': self.SKU,
            'Handle': self.Handle,
            'Title': self.Title,
            'Category': self.Category,
            'Size': self.Size,
            'Color': self.Color,
            'Price': self.Price,
            'Cost': self.Cost,
            'Vendor': self.Vendor,
            'IsCurrent': self.IsCurrent,
            'RowStartDate': self.RowStartDate.isoformat() if self.RowStartDate else None,
            'RowEndDate': self.RowEndDate.isoformat() if self.RowEndDate else None,
        }


class DimDate(db.Model):
    """
    Date Dimension for granular time analytics.
    """
    __tablename__ = 'dim_date'
    __table_args__ = WarehouseModel.get_table_args('dim_date')

    DateKey    = db.Column(db.Integer, primary_key=True) # format YYYYMMDD
    FullDate   = db.Column(db.Date, nullable=False, unique=True)
    Year       = db.Column(db.Integer, nullable=False)
    Quarter    = db.Column(db.Integer, nullable=False)
    Month      = db.Column(db.Integer, nullable=False)
    MonthName  = db.Column(db.String(20), nullable=False)
    Day        = db.Column(db.Integer, nullable=False)
    DayOfWeek  = db.Column(db.String(20), nullable=False)
    IsWeekend  = db.Column(db.Boolean, nullable=False, default=False)


class DimSupplier(db.Model):
    """
    Supplier Dimension.
    """
    __tablename__ = 'dim_supplier'
    __table_args__ = WarehouseModel.get_table_args('dim_supplier')

    SupplierKey   = db.Column(db.Integer, primary_key=True)
    SupplierName  = db.Column(db.String(200), nullable=False, unique=True)
    ContactPerson = db.Column(db.String(100), nullable=True)
    WhatsAppNumber= db.Column(db.String(50), nullable=True)
    Rating        = db.Column(db.Float, default=5.0)
    Status        = db.Column(db.String(50), default='Active')

    def to_dict(self):
        return {
            'SupplierKey': self.SupplierKey,
            'SupplierName': self.SupplierName,
            'ContactPerson': self.ContactPerson,
            'WhatsAppNumber': self.WhatsAppNumber,
            'Rating': self.Rating,
            'Status': self.Status,
        }


class DimChannel(db.Model):
    """
    Sales Channel Dimension.
    """
    __tablename__ = 'dim_channel'
    __table_args__ = WarehouseModel.get_table_args('dim_channel')

    ChannelKey  = db.Column(db.Integer, primary_key=True)
    ChannelName = db.Column(db.String(100), nullable=False, unique=True)


# ─── FACTS ────────────────────────────────────────────────────────────────────

class FactSales(db.Model):
    """
    Sales Fact Table.
    """
    __tablename__ = 'fact_sales'
    __table_args__ = WarehouseModel.get_table_args('fact_sales')

    SalesKey        = db.Column(db.Integer, primary_key=True)
    DateKey         = db.Column(db.Integer, nullable=False) # FK to DimDate
    CustomerKey     = db.Column(db.Integer, nullable=False) # FK to DimCustomer
    ProductKey      = db.Column(db.Integer, nullable=False) # FK to DimProduct
    SupplierKey     = db.Column(db.Integer, nullable=True)  # FK to DimSupplier (linked to manufacturer/vendor)
    ChannelKey      = db.Column(db.Integer, nullable=False) # FK to DimChannel
    
    OrderNumber     = db.Column(db.String(50), nullable=False, index=True)
    Quantity        = db.Column(db.Integer, nullable=False)
    UnitPrice       = db.Column(db.Float, nullable=False)
    UnitCost        = db.Column(db.Float, nullable=False)
    DiscountAmount  = db.Column(db.Float, default=0.0)
    
    # Financial KPI derivations
    GrossRevenue    = db.Column(db.Float, nullable=False) # (Quantity * UnitPrice)
    COGS            = db.Column(db.Float, nullable=False) # (Quantity * UnitCost)
    NetProfit       = db.Column(db.Float, nullable=False) # GrossRevenue - Discount - COGS
    
    FinancialStatus = db.Column(db.String(50), nullable=True)
    FulfillmentStatus=db.Column(db.String(50), nullable=True)
    PaymentMethod   = db.Column(db.String(100), nullable=True)
    RiskLevel       = db.Column(db.String(50), nullable=True)


class FactInventory(db.Model):
    """
    Inventory Snapshot Fact Table.
    """
    __tablename__ = 'fact_inventory'
    __table_args__ = WarehouseModel.get_table_args('fact_inventory')

    InventoryKey    = db.Column(db.Integer, primary_key=True)
    DateKey         = db.Column(db.Integer, nullable=False)
    ProductKey      = db.Column(db.Integer, nullable=False)
    QuantityOnHand  = db.Column(db.Integer, nullable=False)
    ReorderPoint    = db.Column(db.Integer, default=0)
    ReorderQuantity = db.Column(db.Integer, default=0)
    DaysOfSupply    = db.Column(db.Float, nullable=True)
    StockStatus     = db.Column(db.String(50), default='Healthy') # Healthy, Low Stock, Stockout


class FactProcurement(db.Model):
    """
    Procurement Purchase Order Fact Table.
    """
    __tablename__ = 'fact_procurement'
    __table_args__ = WarehouseModel.get_table_args('fact_procurement')

    ProcurementKey    = db.Column(db.Integer, primary_key=True)
    DateKey           = db.Column(db.Integer, nullable=False) # PO requested DateKey
    SupplierKey       = db.Column(db.Integer, nullable=False)
    ProductKey        = db.Column(db.Integer, nullable=False)
    QuantityRequested = db.Column(db.Integer, nullable=False)
    UnitCost          = db.Column(db.Float, nullable=False)
    TotalCost         = db.Column(db.Float, nullable=False)
    LeadTimeDays      = db.Column(db.Integer, nullable=True)
    ReceivedDateKey   = db.Column(db.Integer, nullable=True) # PO received DateKey (null if pending)
    Status            = db.Column(db.String(50), default='Draft') # Draft, Sent, Confirmed, Received, Cancelled


class FactReturns(db.Model):
    """
    Returns and Refunds Fact Table.
    """
    __tablename__ = 'fact_returns'
    __table_args__ = WarehouseModel.get_table_args('fact_returns')

    ReturnKey        = db.Column(db.Integer, primary_key=True)
    DateKey          = db.Column(db.Integer, nullable=False)
    CustomerKey      = db.Column(db.Integer, nullable=False)
    ProductKey       = db.Column(db.Integer, nullable=False)
    OrderNumber      = db.Column(db.String(50), nullable=False, index=True)
    QuantityReturned = db.Column(db.Integer, nullable=False)
    AmountRefunded   = db.Column(db.Float, default=0.0)
    Reason           = db.Column(db.Text, nullable=True)


# ─── PIPELINE LOGGING ─────────────────────────────────────────────────────────

class ETLRun(db.Model):
    """
    Logs ETL execution cycles, rows parsed, and anomalies encountered.
    """
    __tablename__ = 'etl_runs'
    __table_args__ = WarehouseModel.get_table_args('etl_runs')

    id             = db.Column(db.Integer, primary_key=True)
    start_time     = db.Column(db.DateTime, default=datetime.utcnow)
    end_time       = db.Column(db.DateTime, nullable=True)
    status         = db.Column(db.String(50), default='Running') # Running, Completed, Failed
    rows_extracted = db.Column(db.Integer, default=0)
    rows_loaded    = db.Column(db.Integer, default=0)
    errors         = db.Column(db.Text, nullable=True)

    def to_dict(self):
        duration = None
        if self.end_time:
            duration = round((self.end_time - self.start_time).total_seconds(), 1)
        return {
            'id': self.id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': duration,
            'status': self.status,
            'rows_extracted': self.rows_extracted,
            'rows_loaded': self.rows_loaded,
            'errors': self.errors,
        }
