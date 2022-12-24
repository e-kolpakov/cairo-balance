from hypothesis import strategies as st
pubkeys = st.binary(min_size=48, max_size=48)