"""
Stage 1 Logic: Relevance Band Classification

Classifies markets into:
- Trade Ready (was: Structurally Relevant)
- Watch (was: Contextually Watchable)
- Ignore for Now (was: Structurally Uninteresting)
"""


def classify_relevance(context_df):
    """
    Classifies each row into a relevance band based on regime, interaction, warnings.
    
    Inputs:
    - context_df: Output of calculate_trade_ready_context
    
    Output:
    - df with 'relevance_band' column
    """
    if context_df.empty:
        return context_df

    def _get_band(row):
        warnings = row.get('warnings', [])
        regime = row.get('regime_w1', 'TRANSITIONAL')
        interaction = row.get('now_interaction_w1', 'UNKNOWN')
        
        # 1. Ignore if COMPRESSED (regardless of other factors)
        if 'COMPRESSED' in warnings:
            return 'Ignore for Now'
        
        # 2. Ignore if PINNED in BALANCED context (no movement expected)
        if 'PINNED' in warnings and regime == 'BALANCED':
            return 'Ignore for Now'
            
        # 3. Trade Ready (actionable structure)
        # Testing a key level OR Trending/Transitional structure
        if interaction in ['TEST_POC', 'TEST_VAL', 'TEST_VAH']:
            return 'Trade Ready'
        if regime in ['TRENDING', 'TRANSITIONAL']:
            return 'Trade Ready'
            
        # 4. Watch (sound but not yet at actionable levels)
        if regime == 'BALANCED' and interaction == 'INSIDE_VALUE':
            return 'Watch'
            
        return 'Ignore for Now'

    context_df = context_df.copy()
    context_df['relevance_band'] = context_df.apply(_get_band, axis=1)
    return context_df
