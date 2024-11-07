import streamlit as st
import graphviz

# Create a new directed graph
dot = graphviz.Digraph(comment='Odoo Module Menu Structure')
dot.attr(rankdir='TB')

# Add nodes for main menu items
dot.node('root', 'Cheque Management')

# Main categories
main_categories = [
    'Cheque Books', 'Categories', 'Operations', 
    'Payment Processing', 'Branch Management'
]

# Add main category nodes and connect to root
for category in main_categories:
    dot.node(category.lower().replace(' ', '_'), category)
    dot.edge('root', category.lower().replace(' ', '_'))

# Add subcategories
operations_sub = [
    'Incoming Cheques', 'Outgoing Cheques',
    'Transfers', 'Returns', 'Deposits'
]

for sub in operations_sub:
    dot.node(sub.lower().replace(' ', '_'), sub)
    dot.edge('operations', sub.lower().replace(' ', '_'))

# Payment processing subcategories
payment_sub = [
    'Digital Wallets', 'Bank Transfers',
    'Credit/Debit Cards'
]

for sub in payment_sub:
    dot.node(sub.lower().replace(' ', '_'), sub)
    dot.edge('payment_processing', sub.lower().replace(' ', '_'))

# Branch management subcategories
branch_sub = [
    'Branch Hierarchy', 'Access Control',
    'Inter-branch Transfers'
]

for sub in branch_sub:
    dot.node(sub.lower().replace(' ', '_'), sub)
    dot.edge('branch_management', sub.lower().replace(' ', '_'))

# Streamlit app
st.title('Odoo Module Menu Structure Visualization')
st.graphviz_chart(dot.source)
