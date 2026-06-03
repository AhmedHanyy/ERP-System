from app import db
from datetime import datetime
import os

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
    Customer Dimension — sourced from Shopify customers_export.csv.
    All fields traceable to a real Shopify Customer ID.
    """
    __tablename__ = 'dim_customer'
    __table_args__ = WarehouseModel.get_table_args('dim_customer')

    CustomerKey         = db.Column(db.Integer, primary_key=True)
    ShopifyCustomerID   = db.Column(db.String(100), unique=True, nullable=True, index=True)
    FirstName           = db.Column(db.String(100), nullable=True)
    LastName            = db.Column(db.String(100), nullable=True)
    Email               = db.Column(db.String(150), nullable=True, index=True)
    Phone               = db.Column(db.String(50), nullable=True)
    City                = db.Column(db.String(100), nullable=True)
    Region              = db.Column(db.String(100), nullable=True)  # Normalized Governorate
    Country             = db.Column(db.String(10), nullable=True, default='EG')
    AcceptsMarketing    = db.Column(db.Boolean, default=False)
    RFM_Segment         = db.Column(db.String(50), nullable=True)

    # ── Business Context (audit requirement) ──────────────────────────────────
    CustomerTags        = db.Column(db.String(500), nullable=True)  # Fraud, Banned, Bad Customer, newsletter
    CustomerNote        = db.Column(db.Text, nullable=True)         # Free-text manual notes from Shopify
    IsFraudRisk         = db.Column(db.Boolean, default=False)      # True if Tags contains Fraud/Banned/Bad Customer
    LifetimeTotalSpent  = db.Column(db.Float, default=0.0)          # From Shopify Total Spent column
    LifetimeTotalOrders = db.Column(db.Integer, default=0)          # From Shopify Total Orders column

    created_at          = db.Column(db.DateTime, default=datetime.utcnow)

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
            'CustomerTags': self.CustomerTags,
            'IsFraudRisk': self.IsFraudRisk,
            'LifetimeTotalSpent': self.LifetimeTotalSpent,
            'LifetimeTotalOrders': self.LifetimeTotalOrders,
        }


class DimProduct(db.Model):
    """
    Product Dimension (SCD Type 2) — sourced from Shopify products_export_1.csv.
    All fields traceable to a real Shopify product Handle or SKU.
    """
    __tablename__ = 'dim_product'
    __table_args__ = WarehouseModel.get_table_args('dim_product')

    ProductKey      = db.Column(db.Integer, primary_key=True)
    SKU             = db.Column(db.String(100), nullable=False, index=True)  # Business key (not unique due to SCD2)
    Handle          = db.Column(db.String(200), nullable=True, index=True)   # Shopify product handle (traceability)
    Title           = db.Column(db.String(300), nullable=False)
    Category        = db.Column(db.String(200), nullable=True)               # Shopify Product Category (taxonomy)
    ProductType     = db.Column(db.String(150), nullable=True)               # Shopify Type ("Printed Oversized T-Shirt")
    Size            = db.Column(db.String(50), nullable=True)                # Variant size (S, M, L, XL, 2XL)
    Color           = db.Column(db.String(100), nullable=True)               # From color metafield
    Fabric          = db.Column(db.String(100), nullable=True)               # cotton, linen, etc.
    TargetGender    = db.Column(db.String(50), nullable=True)                # unisex, female, male
    SizesOffered    = db.Column(db.String(200), nullable=True)               # "s; m; l; xl; 2xl"
    Barcode         = db.Column(db.String(50), nullable=True)                # EAN barcode

    ProductFamily   = db.Column(db.String(150), nullable=True)               # Clean product family name
    Fit             = db.Column(db.String(50), nullable=True)                # Parsed fit (Oversized, Cropped, etc.)
    Graphic         = db.Column(db.String(100), nullable=True)               # Parsed graphic/design (or Plain)
    VariantName     = db.Column(db.String(150), nullable=True)               # Color / Size combination
    Price           = db.Column(db.Float, nullable=False)
    CompareAtPrice  = db.Column(db.Float, nullable=True)                     # Original price before markdown
    Cost            = db.Column(db.Float, nullable=False)
    IsCostEstimated = db.Column(db.Boolean, default=True)                    # True = cost came from ratio fallback

    Vendor          = db.Column(db.String(100), nullable=True, default='Leveld')
    Status          = db.Column(db.String(50), default='active')
    IsActive        = db.Column(db.Boolean, default=True)

    # ── SCD Type 2 Fields ────────────────────────────────────────────────────
    RowStartDate    = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    RowEndDate      = db.Column(db.DateTime, nullable=True)
    IsCurrent       = db.Column(db.Boolean, nullable=False, default=True, index=True)

    def to_dict(self):
        return {
            'ProductKey': self.ProductKey,
            'SKU': self.SKU,
            'Handle': self.Handle,
            'Title': self.Title,
            'Category': self.Category,
            'ProductType': self.ProductType,
            'ProductFamily': self.ProductFamily,
            'Fit': self.Fit,
            'Graphic': self.Graphic,
            'VariantName': self.VariantName,
            'Size': self.Size,
            'Color': self.Color,
            'Fabric': self.Fabric,
            'TargetGender': self.TargetGender,
            'SizesOffered': self.SizesOffered,
            'Price': self.Price,
            'CompareAtPrice': self.CompareAtPrice,
            'Cost': self.Cost,
            'IsCostEstimated': self.IsCostEstimated,
            'Vendor': self.Vendor,
            'IsCurrent': self.IsCurrent,
            'RowStartDate': self.RowStartDate.isoformat() if self.RowStartDate else None,
            'RowEndDate': self.RowEndDate.isoformat() if self.RowEndDate else None,
        }


class DimDate(db.Model):
    """Date Dimension for time-series analytics."""
    __tablename__ = 'dim_date'
    __table_args__ = WarehouseModel.get_table_args('dim_date')

    DateKey    = db.Column(db.Integer, primary_key=True)  # YYYYMMDD
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
    IsReal=False records are demo/simulation stubs until real Excel data is loaded.
    Leveld has no real third-party supplier data in Shopify — all vendor = 'Leveld'.
    """
    __tablename__ = 'dim_supplier'
    __table_args__ = WarehouseModel.get_table_args('dim_supplier')

    SupplierKey      = db.Column(db.Integer, primary_key=True)
    SupplierName     = db.Column(db.String(200), nullable=False, unique=True)
    ContactPerson    = db.Column(db.String(100), nullable=True)
    Phone            = db.Column(db.String(50), nullable=True)
    SupplierType     = db.Column(db.String(100), nullable=True)  # Blank Garment / Print Shop / Fabric / Packaging
    Country          = db.Column(db.String(100), nullable=True, default='Egypt')
    LeadTimeDays_Avg = db.Column(db.Integer, nullable=True)
    MinOrderQty      = db.Column(db.Integer, nullable=True)
    Rating           = db.Column(db.Float, default=4.5)
    Status           = db.Column(db.String(50), default='Active')
    IsReal           = db.Column(db.Boolean, default=False)  # False = demo stub; True = from real Excel

    def to_dict(self):
        return {
            'SupplierKey': self.SupplierKey,
            'SupplierName': self.SupplierName,
            'ContactPerson': self.ContactPerson,
            'Phone': self.Phone,
            'SupplierType': self.SupplierType,
            'Country': self.Country,
            'LeadTimeDays_Avg': self.LeadTimeDays_Avg,
            'MinOrderQty': self.MinOrderQty,
            'Rating': self.Rating,
            'Status': self.Status,
            'IsReal': self.IsReal,
        }


class DimChannel(db.Model):
    """Sales Channel Dimension. Leveld uses Online Storefront only (ChannelKey=1)."""
    __tablename__ = 'dim_channel'
    __table_args__ = WarehouseModel.get_table_args('dim_channel')

    ChannelKey  = db.Column(db.Integer, primary_key=True)
    ChannelName = db.Column(db.String(100), nullable=False, unique=True)


# ─── FACTS ────────────────────────────────────────────────────────────────────

class FactSales(db.Model):
    """
    Sales Fact Table.
    Real records: OrderNumber = '#LV-XXXX', IsSynthetic = False
    Synthetic records: OrderNumber = '#SYN-XXXX', IsSynthetic = True
    """
    __tablename__ = 'fact_sales'
    __table_args__ = WarehouseModel.get_table_args('fact_sales')

    SalesKey         = db.Column(db.Integer, primary_key=True)
    DateKey          = db.Column(db.Integer, nullable=False, index=True)
    CustomerKey      = db.Column(db.Integer, nullable=False, index=True)
    ProductKey       = db.Column(db.Integer, nullable=False, index=True)
    SupplierKey      = db.Column(db.Integer, nullable=True)
    ChannelKey       = db.Column(db.Integer, nullable=False, default=1)

    # ── Traceability ─────────────────────────────────────────────────────────
    OrderNumber      = db.Column(db.String(50), nullable=False, index=True)  # #LV-XXXX or #SYN-XXXX
    ShopifyOrderID   = db.Column(db.String(50), nullable=True)               # Shopify numeric ID (real orders only)
    IsSynthetic      = db.Column(db.Boolean, nullable=False, default=False)  # False=real, True=generated
    IsCancelled      = db.Column(db.Boolean, nullable=False, default=False)  # True if Cancelled at is set

    # ── Line Item Financials ──────────────────────────────────────────────────
    Quantity         = db.Column(db.Integer, nullable=False)
    UnitPrice        = db.Column(db.Float, nullable=False)
    CompareAtPrice   = db.Column(db.Float, nullable=True)    # Original price before markdown
    UnitCost         = db.Column(db.Float, nullable=False)
    DiscountAmount   = db.Column(db.Float, default=0.0)      # Line-item discount
    GrossRevenue     = db.Column(db.Float, nullable=False)   # Quantity * UnitPrice
    COGS             = db.Column(db.Float, nullable=False)   # Quantity * UnitCost
    NetProfit        = db.Column(db.Float, nullable=False)   # GrossRevenue - DiscountAmount - COGS

    # ── Order-Level Context ───────────────────────────────────────────────────
    DiscountCode     = db.Column(db.String(100), nullable=True)  # LEVELD10, FREESHIPPING, etc.
    OrderSubtotal    = db.Column(db.Float, nullable=True)        # Order-level subtotal
    OrderShipping    = db.Column(db.Float, nullable=True)        # Shipping cost (60-150 EGP)

    # ── Status ────────────────────────────────────────────────────────────────
    FinancialStatus  = db.Column(db.String(50), nullable=True)   # paid, pending, voided
    FulfillmentStatus= db.Column(db.String(50), nullable=True)   # fulfilled, unfulfilled, partial
    PaymentMethod    = db.Column(db.String(100), nullable=True)  # Cash on Delivery (COD), manual
    RiskLevel        = db.Column(db.String(50), nullable=True, default='Low')


class FactInventory(db.Model):
    """
    Inventory Snapshot Fact Table.
    Current-state snapshot from Shopify products_export_1.csv Variant Inventory Qty.
    """
    __tablename__ = 'fact_inventory'
    __table_args__ = WarehouseModel.get_table_args('fact_inventory')

    InventoryKey    = db.Column(db.Integer, primary_key=True)
    DateKey         = db.Column(db.Integer, nullable=False)
    ProductKey      = db.Column(db.Integer, nullable=False)
    QuantityOnHand  = db.Column(db.Integer, nullable=False)
    ReorderPoint    = db.Column(db.Integer, default=5)
    ReorderQuantity = db.Column(db.Integer, default=50)
    DaysOfSupply    = db.Column(db.Float, nullable=True)
    StockStatus     = db.Column(db.String(50), default='Healthy')  # Healthy, Low Stock, Stockout


class FactProcurement(db.Model):
    """
    Procurement Purchase Order Fact Table.
    IMPORTANT: IsReal=False rows are simulated demo data.
    Real procurement data awaits external Excel supplier input.
    Do NOT use simulated procurement for supplier performance KPIs.
    """
    __tablename__ = 'fact_procurement'
    __table_args__ = WarehouseModel.get_table_args('fact_procurement')

    ProcurementKey    = db.Column(db.Integer, primary_key=True)
    DateKey           = db.Column(db.Integer, nullable=False)
    SupplierKey       = db.Column(db.Integer, nullable=False)
    ProductKey        = db.Column(db.Integer, nullable=False)
    QuantityRequested = db.Column(db.Integer, nullable=False)
    UnitCost          = db.Column(db.Float, nullable=False)
    TotalCost         = db.Column(db.Float, nullable=False)
    LeadTimeDays      = db.Column(db.Integer, nullable=True)
    ReceivedDateKey   = db.Column(db.Integer, nullable=True)
    Status            = db.Column(db.String(50), default='Draft')
    IsReal            = db.Column(db.Boolean, default=False)  # False = demo/simulated


class FactReturns(db.Model):
    """
    Returns and Refunds Fact Table.
    Kept empty — Shopify export shows 0 refunded amounts.
    Schema preserved for future use.
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
    """Logs ETL execution cycles."""
    __tablename__ = 'etl_runs'
    __table_args__ = WarehouseModel.get_table_args('etl_runs')

    id               = db.Column(db.Integer, primary_key=True)
    start_time       = db.Column(db.DateTime, default=datetime.utcnow)
    end_time         = db.Column(db.DateTime, nullable=True)
    status           = db.Column(db.String(50), default='Running')  # Running, Completed, Failed
    rows_extracted   = db.Column(db.Integer, default=0)
    rows_loaded      = db.Column(db.Integer, default=0)
    real_rows        = db.Column(db.Integer, default=0)
    synthetic_rows   = db.Column(db.Integer, default=0)
    errors           = db.Column(db.Text, nullable=True)

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
            'real_rows': self.real_rows,
            'synthetic_rows': self.synthetic_rows,
            'errors': self.errors,
        }
