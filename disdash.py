import requests
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import plotly.express as px
import pytz
import config

# Function to fetch groups a user is in from Hypothesis API
def fetch_user_groups(api_key):
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get("https://hypothes.is/api/profile/groups", headers=headers)

    if response.status_code == 200:
        groups_data = response.json()
        groups_info = {group['name']: group['id'] for group in groups_data}
        return groups_info
    else:
        st.error("Failed to fetch user groups.")
        return None

# Function to fetch student posts from Hypothesis API
def fetch_student_posts(api_key, group):
    # Construct API endpoint and headers
    api_url = "https://hypothes.is/api/search"  # Replace with Hypothesis API endpoint
    headers = {"Authorization": f"Bearer {api_key}"}

    # Set date range for the past week
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    params = {
        "group": group,  # Replace with your group name or ID
        "sort": "updated",
        "search_after": start_date.isoformat(),
        "search_before": end_date.isoformat(),
        "limit": 200,  # Adjust limit as needed
    }

    # Make GET request to Hypothesis API
    response = requests.get(api_url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()["rows"]
    else:
        return None

# Function to count annotations and replies by students and create DataFrame
def count_posts_by_student(posts):
    annotations_count = {}
    replies_count = {}
    for post in posts:
        user = post["user"]
        user_name = user.split(":")[-1].split("@")[0]  # Extracting user_name
        
        # Check if the post is an annotation or a reply
        if "references" not in post:
            if user_name not in annotations_count:
                annotations_count[user_name] = 1
            else:
                annotations_count[user_name] += 1
        else:
            if user_name not in replies_count:
                replies_count[user_name] = 1
            else:
                replies_count[user_name] += 1
    
    # Create DataFrames for annotations and replies
    annotations_df = pd.DataFrame(annotations_count.items(), columns=["Student", "Annotations"])
    replies_df = pd.DataFrame(replies_count.items(), columns=["Student", "Replies"])

    # Merge the DataFrames on 'Student' column
    merged_df = pd.merge(annotations_df, replies_df, on="Student", how="outer").fillna(0)
    return merged_df

# Function to create heatmap data with date in US Eastern timezone and mm/dd format
def create_heatmap_data(posts):
    heatmap_data = {}
    eastern = pytz.timezone('US/Eastern')
    for post in posts:
        user = post["user"]
        user_name = user.split(":")[-1].split("@")[0]  # Extracting user_name
        
        # Convert created date to US Eastern timezone and format to mm/dd
        created_date = datetime.fromisoformat(post["created"].replace('Z', '')).astimezone(eastern).strftime('%m/%d')

        # Initialize the dictionary if the user is not already present
        if user_name not in heatmap_data:
            heatmap_data[user_name] = {}

        # Increment the count for the specific date
        if created_date not in heatmap_data[user_name]:
            heatmap_data[user_name][created_date] = 1
        else:
            heatmap_data[user_name][created_date] += 1

    # Create DataFrame from the dictionary
    heatmap_df = pd.DataFrame.from_dict(heatmap_data, orient='index').fillna(0)
    
    # Sort the DataFrame columns (dates) in chronological order
    heatmap_df = heatmap_df.reindex(sorted(heatmap_df.columns, key=lambda x: datetime.strptime(x, '%m/%d')), axis=1)
    return heatmap_df

# Main Streamlit app
def main():
    st.title("Student Posts Dashboard")
    
    # Get API key from user input (for demonstration purposes)
    api_key = st.sidebar.text_input("Enter your Hypothesis API key", type="password")
    # api_key = config.HYPOTHESIS_API_TOKEN

    if api_key:
        # Fetch groups the user is in
        user_groups = fetch_user_groups(api_key)

        if user_groups:
            st.sidebar.title("Select Hypothesis Group")
            selected_group_name = st.sidebar.selectbox("Select Group", list(user_groups.keys()))
            selected_group_id = user_groups[selected_group_name]


            st.write(f"You've selected the group: {selected_group_name}")

            # Fetch student posts
            posts = fetch_student_posts(api_key, selected_group_id)
            # st.write(posts)

            if posts:
                # Count posts by student and create DataFrame
                student_post_df = count_posts_by_student(posts)

                # Sort the DataFrame by 'Student' column (user_name)
                student_post_df.sort_values(by='Student', inplace=True)

                # Display DataFrame as a table
                st.subheader("Number of Posts by Student (Past Week)")
                st.write(student_post_df)

                # Create heatmap data for posts by student on each day
                st.subheader("Number of Posts by Student on Each Day (Past Week)")
                heatmap_df = create_heatmap_data(posts)

                # Sort the DataFrame by 'Student' column (user_name)
                heatmap_df.sort_index(inplace=True)

                st.write(heatmap_df)


                # Display DataFrame as an interactive heatmap using Plotly
                st.subheader("Number of Posts by Student on Each Day (Interactive Heatmap)")
                fig = px.imshow(heatmap_df, color_continuous_scale='YlGnBu')
                fig.update_layout(
                    xaxis=dict(
                        title='Date',
                        tickmode='array',
                        tickvals=list(range(len(heatmap_df.columns))),
                        ticktext=list(heatmap_df.columns),
                        tickangle=0  # Set the angle of the x-axis ticks to horizontal
                    ),
                    yaxis=dict(title='Student')
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.write("Failed to fetch student posts. Please check your API key or try again.")
        else:
            st.warning("No groups found. Please check your Hypothesis account or try again.")

        
    else:
        st.write("Please enter your Hypothesis API key.")

if __name__ == "__main__":
    main()
