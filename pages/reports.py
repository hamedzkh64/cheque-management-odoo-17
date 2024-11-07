import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os

# Add the root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.cheque_manage import ChequeManage
from models.cheque_category import ChequeCategory
from models.cheque_book import ChequeBook

def load_data():
    """Load cheque data from the database"""
    cheques = ChequeManage.search([])
    data = []
    for cheque in cheques:
        data.append({
            'seq_no': cheque.seq_no,
            'payer': cheque.payer.name if cheque.payer else '',
            'amount': cheque.amount,
            'cheque_date': cheque.cheque_date,
            'due_date': cheque.due_date,
            'state': cheque.state,
            'category': cheque.category_id.name if cheque.category_id else '',
            'branch_code': cheque.branch_code,
            'bank_name': cheque.cheque_book_id.bank_name if cheque.cheque_book_id else ''
        })
    return pd.DataFrame(data)

def main():
    st.title("Advanced Cheque Management Reports")
    
    # Load data
    df = load_data()
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Date range filter
    st.sidebar.subheader("Date Range")
    date_filter = st.sidebar.selectbox(
        "Filter by",
        ["Cheque Date", "Due Date"]
    )
    
    min_date = df[date_filter].min() if not df.empty else datetime.now()
    max_date = df[date_filter].max() if not df.empty else datetime.now()
    
    start_date = st.sidebar.date_input("Start Date", min_date)
    end_date = st.sidebar.date_input("End Date", max_date)
    
    # Category filter
    categories = ['All'] + list(df['category'].unique())
    selected_category = st.sidebar.selectbox("Category", categories)
    
    # Status filter
    statuses = ['All'] + list(df['state'].unique())
    selected_status = st.sidebar.selectbox("Status", statuses)
    
    # Amount range filter
    min_amount = float(df['amount'].min()) if not df.empty else 0
    max_amount = float(df['amount'].max()) if not df.empty else 1000000
    amount_range = st.sidebar.slider(
        "Amount Range",
        min_value=min_amount,
        max_value=max_amount,
        value=(min_amount, max_amount)
    )
    
    # Apply filters
    mask = (df[date_filter] >= pd.to_datetime(start_date)) & \
           (df[date_filter] <= pd.to_datetime(end_date)) & \
           (df['amount'] >= amount_range[0]) & \
           (df['amount'] <= amount_range[1])
    
    if selected_category != 'All':
        mask &= df['category'] == selected_category
    if selected_status != 'All':
        mask &= df['state'] == selected_status
    
    filtered_df = df[mask]
    
    # Display summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Cheques", len(filtered_df))
    with col2:
        st.metric("Total Amount", f"${filtered_df['amount'].sum():,.2f}")
    with col3:
        st.metric("Average Amount", f"${filtered_df['amount'].mean():,.2f}")
    
    # Visualizations
    st.subheader("Cheque Status Distribution")
    fig_status = px.pie(filtered_df, names='state', title='Cheque Status Distribution')
    st.plotly_chart(fig_status)
    
    st.subheader("Amount by Category")
    fig_category = px.bar(
        filtered_df.groupby('category')['amount'].sum().reset_index(),
        x='category',
        y='amount',
        title='Total Amount by Category'
    )
    st.plotly_chart(fig_category)
    
    st.subheader("Timeline of Cheques")
    fig_timeline = px.scatter(
        filtered_df,
        x='cheque_date',
        y='amount',
        color='state',
        size='amount',
        hover_data=['seq_no', 'payer'],
        title='Cheque Timeline'
    )
    st.plotly_chart(fig_timeline)
    
    # Data table with export option
    st.subheader("Detailed Report")
    st.dataframe(filtered_df)
    
    # Export functionality
    if st.button("Export to Excel"):
        output = filtered_df.to_excel(index=False)
        st.download_button(
            label="Download Excel file",
            data=output,
            file_name="cheque_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    main()
