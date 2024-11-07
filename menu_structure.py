import streamlit as st
import graphviz

def create_menu_structure():
    # Create a new directed graph
    dot = graphviz.Digraph(comment='Cheque Management Menu Structure')
    dot.attr(rankdir='TB', splines='ortho')
    
    # Style configurations
    dot.attr('node', shape='box', style='rounded,filled', fillcolor='lightblue')
    
    # Main menu node
    dot.node('root', 'Cheque Management\nModule', shape='doubleoctagon', fillcolor='lightgreen')
    
    # Main categories
    main_categories = {
        'cheque_book': 'Cheque Books\nManagement',
        'category': 'Categories\nConfiguration',
        'cheque_manage': 'Cheque\nOperations',
        'payment': 'Payment\nProcessing',
        'branch': 'Branch\nManagement'
    }
    
    for key, label in main_categories.items():
        dot.node(key, label)
        dot.edge('root', key)
    
    # Cheque Book Operations
    book_ops = {
        'book_create': 'Create\nCheque Book',
        'book_leaves': 'Leaf\nGeneration',
        'book_track': 'Track\nSaad Numbers'
    }
    
    for key, label in book_ops.items():
        dot.node(key, label, fillcolor='lightyellow')
        dot.edge('cheque_book', key)
    
    # Cheque Operations
    cheque_ops = {
        'incoming': 'Incoming\nCheques',
        'outgoing': 'Outgoing\nCheques',
        'transfer': 'Inter-branch\nTransfers'
    }
    
    for key, label in cheque_ops.items():
        dot.node(key, label, fillcolor='lightpink')
        dot.edge('cheque_manage', key)
    
    # Payment Processing
    payment_ops = {
        'digital_wallet': 'Digital\nWallet',
        'bank_transfer': 'Bank\nTransfer',
        'card_payment': 'Card\nPayments'
    }
    
    for key, label in payment_ops.items():
        dot.node(key, label, fillcolor='lightcyan')
        dot.edge('payment', key)
    
    # Branch Operations
    branch_ops = {
        'branch_coord': 'Branch\nCoordination',
        'branch_access': 'Access\nControl',
        'branch_transfer': 'Transfer\nManagement'
    }
    
    for key, label in branch_ops.items():
        dot.node(key, label, fillcolor='lightgrey')
        dot.edge('branch', key)
    
    return dot

def main():
    st.set_page_config(
        page_title="Cheque Management Menu Structure",
        layout="wide"
    )
    
    st.title("🏦 Cheque Management Module - Menu Structure")
    st.write("Interactive visualization of the complete menu structure and module organization")
    
    # Create and display the menu structure
    dot = create_menu_structure()
    st.graphviz_chart(dot.source)
    
    # Add detailed description
    st.markdown("""
    ### 📋 Module Components Description
    
    #### 1. Cheque Books Management
    - Create and configure new cheque books
    - Automated leaf generation with sequential numbering
    - Track Saad numbers and maintain serial number sequences
    
    #### 2. Categories Configuration
    - Define cheque categories for different purposes
    - Configure accounting rules and journal entries
    - Set up validation and processing rules
    
    #### 3. Cheque Operations
    - Process incoming cheques with validation
    - Manage outgoing cheques and payments
    - Handle inter-branch cheque transfers
    
    #### 4. Payment Processing
    - Integrate with digital wallet systems
    - Process bank transfers
    - Handle card payment transactions
    
    #### 5. Branch Management
    - Coordinate operations across multiple branches
    - Manage branch-specific access controls
    - Handle inter-branch transfer workflows
    """)

if __name__ == "__main__":
    main()
