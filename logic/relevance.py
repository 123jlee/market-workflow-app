def classify_relevance(context_df):
    """
    Inputs:
    - context_df: Output of calculate_context_primitives.
    
    Output:
    - df with 'relevance_band' column.
    """
    if context_df.empty:
        return context_df

    def _get_band(row):
        flags = row['flags']
        state = row['weekly_auction_state']
        loc_w = row['price_loc_w']
        align = row['dw_alignment']
        
        # 1. Uninteresting - Only if COMPRESSION, or PINNED in BALANCED context
        if 'COMPRESSION' in flags:
            return 'Structurally Uninteresting'
        if 'PINNED' in flags and state == 'BALANCED':
            return 'Structurally Uninteresting'
            
        # 2. Relevant (Ready for Action)
        # Testing a key level OR Trending/Transitional structure
        if loc_w == 'TEST_POC':
            return 'Structurally Relevant'
        if state in ['TRENDING', 'TRANSITIONAL']:
            return 'Structurally Relevant'
            
        # 3. Watchable (Sound but not active)
        if state == 'BALANCED' and loc_w == 'INSIDE':
            return 'Contextually Watchable'
            
        return 'Structurally Uninteresting'

    context_df['relevance_band'] = context_df.apply(_get_band, axis=1)
    return context_df
