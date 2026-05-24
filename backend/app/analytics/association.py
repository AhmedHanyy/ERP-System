"""
Market Basket Analysis (Association Rules)
──────────────────────────────────────────
Method: Apriori algorithm (mlxtend) on order transaction data

Outputs association rules with:
  - Support    = How often items appear together
  - Confidence = P(B | A)
  - Lift       = How much more likely than by chance

Use cases:
  - Cross-sell recommendations ("customers who buy X also buy Y")
  - Product placement decisions
  - Bundle promotions

NOTE: When real dataset arrives:
  - Tune min_support and min_confidence thresholds based on actual transaction density
  - Consider time-windowed analysis (seasonal baskets)
"""
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
from .etl import extract_sales_data


def run_market_basket(min_support: float = 0.02, min_confidence: float = 0.3) -> dict:
    """
    Run Apriori on order-level baskets.
    Returns: frequent itemsets + association rules.
    """
    df = extract_sales_data()

    if df.empty:
        return {'error': 'No data', 'rules': [], 'itemsets': []}

    # Build transaction baskets (one row per order, columns = products)
    baskets = df.groupby(['order_id', 'product_name'])['quantity'].sum().unstack(fill_value=0)
    baskets = baskets.applymap(lambda x: True if x > 0 else False)

    # Apriori
    try:
        # Try a lower support threshold of 0.005 if no data found with 0.02
        support_to_use = min_support
        frequent_itemsets = apriori(baskets, min_support=support_to_use, use_colnames=True, max_len=3)
        
        if frequent_itemsets.empty:
            frequent_itemsets = apriori(baskets, min_support=0.005, use_colnames=True, max_len=3)

        if frequent_itemsets.empty:
             return {'error': 'Not enough data patterns identified yet. Try increasing order diversity.', 'rules': [], 'itemsets': []}

        rules = association_rules(frequent_itemsets, metric='confidence', min_threshold=min_confidence)
        rules = rules.sort_values('lift', ascending=False)
    except Exception as e:
        return {'error': str(e), 'rules': [], 'itemsets': []}

    # Format rules
    rules_data = [
        {
            'antecedents': list(row['antecedents']),
            'consequents': list(row['consequents']),
            'support': round(float(row['support']), 4),
            'confidence': round(float(row['confidence']), 4),
            'lift': round(float(row['lift']), 4),
            'interpretation': f"Customers who buy {', '.join(row['antecedents'])} "
                              f"also tend to buy {', '.join(row['consequents'])} "
                              f"({round(row['confidence']*100,1)}% of the time, "
                              f"{round(row['lift'],2)}x more likely)"
        }
        for _, row in rules.head(30).iterrows()
    ]

    # Frequent itemsets
    itemsets_data = [
        {
            'items': list(row['itemsets']),
            'support': round(float(row['support']), 4),
            'size': len(row['itemsets'])
        }
        for _, row in frequent_itemsets.sort_values('support', ascending=False).head(20).iterrows()
    ]

    return {
        'rules': rules_data,
        'itemsets': itemsets_data,
        'model_info': {
            'method': 'Apriori (mlxtend)',
            'min_support': min_support,
            'min_confidence': min_confidence,
            'total_transactions': len(baskets),
            'rules_found': len(rules),
        }
    }


def get_product_recommendations(product_name: str) -> list:
    """Given a product, return its top associated products."""
    result = run_market_basket()
    rules  = result.get('rules', [])
    recommendations = []
    for rule in rules:
        if product_name in rule['antecedents']:
            recommendations.append({
                'recommended': rule['consequents'],
                'confidence': rule['confidence'],
                'lift': rule['lift'],
            })
    return sorted(recommendations, key=lambda x: x['lift'], reverse=True)[:5]
