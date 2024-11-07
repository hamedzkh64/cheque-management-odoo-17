import streamlit as st
import graphviz
import json

def create_menu_structure():
    # Create a new directed graph
    dot = graphviz.Digraph()
    dot.attr(rankdir='LR')
    
    # Main menu nodes
    dot.node('cheque_management', 'Cheque Management')
    
    # Category nodes
    categories = [
        'cheque_book', 'Cheque Books',
        'cheque_category', 'Categories',
        'cheque_manage', 'Cheque Management',
        'payment_processor', 'Payment Processors',
        'cheque_branch', 'Branches'
    ]
    
    for i in range(0, len(categories), 2):
        dot.node(categories[i], categories[i+1])
        dot.edge('cheque_management', categories[i])
    
    # Sub-menu nodes for Cheque Management
    cheque_actions = [
        ('incoming', 'Incoming Cheques'),
        ('outgoing', 'Outgoing Cheques'),
        ('transfer', 'Transfers'),
        ('reports', 'Reports')
    ]
    
    for action_id, label in cheque_actions:
        dot.node(f'action_{action_id}', label)
        dot.edge('cheque_manage', f'action_{action_id}')
    
    # Report sub-menu
    report_types = [
        ('status', 'Status Report'),
        ('analytics', 'Analytics'),
        ('cash_flow', 'Cash Flow')
    ]
    
    for report_id, label in report_types:
        dot.node(f'report_{report_id}', label)
        dot.edge('action_reports', f'report_{report_id}')
    
    return dot

def main():
    st.title("Cheque Management Module - Menu Structure")
    st.write("This visualization shows the complete menu structure of the Odoo Cheque Management module.")
    
    # Create the menu structure visualization
    dot = create_menu_structure()
    
    # Render the graph
    st.graphviz_chart(dot)
    
    # Add legend/description
    st.markdown("""
    ### Menu Structure Description
    
    1. **Cheque Books**
        - Manage checkbooks and leaf generation
        - Track Saad numbers and serial numbers
        
    2. **Categories**
        - Configure cheque categories
        - Set up accounting rules
        
    3. **Cheque Management**
        - Incoming Cheques: Handle received cheques
        - Outgoing Cheques: Manage issued cheques
        - Transfers: Inter-branch transfers
        - Reports: Various reporting options
        
    4. **Payment Processors**
        - Configure payment methods
        - Digital wallet integration
        
    5. **Branches**
        - Multi-branch coordination
        - Branch-specific settings
    """)

if __name__ == "__main__":
    main()
