import pandas as pd

# Load the Excel file or create a new DataFrame if the file doesn't exist
try:
    df = pd.read_excel("watched_mov.xlsx")
except FileNotFoundError:
    df = pd.DataFrame(columns=["Movie Name", "Release Year", "Rating (1-5)"])

# Prompt user for movie name, release year, and rating
movie_name = input("Enter the movie name: ")
release_year = int(input("Enter the release year: "))
rating = float(input("Enter the rating(1-5): "))

# Append the new data to the DataFrame
new_row = {"Movie Name": movie_name, "Release Year": release_year, "Rating (1-5)": rating}
df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

# Sort the DataFrame alphabetically by movie name and then by release year
df.sort_values(by=["Movie Name"], ascending=True, inplace=True)
df.sort_values(by=["Release Year"], ascending=True, inplace=True, ignore_index=True)

# Write the sorted DataFrame back to the Excel file
df.to_excel("watched_mov.xlsx", index=False)

print("Data added and sorted successfully.")
