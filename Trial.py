import pandas as pd

# Load the Excel file or create a new DataFrame if the file doesn't exist
try:
    df = pd.read_excel("watched_mov.xlsx")
except FileNotFoundError:
    df = pd.DataFrame(columns=["Movie Name", "Release Year", "Rating (1-5)", "Adult Content", "Kissing"])

# Prompt user for movie details
movie_name = input("Enter the title of the movie: ")
release_year = int(input("Enter the release year of the movie: "))
overall_rating = float(input("Enter the overall rating of the movie (1-5): "))
adult_content = input("Does the movie contain adult content? (Yes or No): ")
kissing = input("Does the movie contain kissing scenes? (Yes or No): ")

# Validate overall rating
if overall_rating < 1 or overall_rating > 5:
    print("Invalid overall rating. Please enter a number between 1 and 5.")
else:
    # Normalize adult content, kissing, and nudity inputs
    adult_content = "Yes" if adult_content.lower() == "yes" else "No"
    kissing = "Yes" if kissing.lower() == "yes" else "No"

    # Append the new data to the DataFrame
    new_row = {
        "Movie Name": movie_name,
        "Release Year": release_year,
        "Rating (1-5)": overall_rating,
        "Adult Content": adult_content, 
        "Kissing": kissing
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    # Sort the DataFrame alphabetically by movie name and then by release year
    df.sort_values(by=["Movie Name", "Release Year"], ascending=[True, True], inplace=True, ignore_index=True)

    # Write the sorted DataFrame back to the Excel file
    df.to_excel("watched_mov.xlsx", index=False)

    print("Data added and sorted successfully.")
