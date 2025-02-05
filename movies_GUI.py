import pandas as pd
import tkinter as tk
from tkinter import messagebox, simpledialog

# Function to add data to the DataFrame and save it
def add_data(movie_name, release_year, rating):
    new_row = {"Movie Name": movie_name, "Release Year": release_year, "Rating (1-5)": rating}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.sort_values(by=["Movie Name", "Release Year"], ascending=[True, True], inplace=True, ignore_index=True)
    df.to_excel("watched_mov.xlsx", index=False)
    messagebox.showinfo("Success", "Data added and sorted successfully.")

# Load the Excel file or create a new DataFrame if the file doesn't exist
try:
    df = pd.read_excel("watched_mov.xlsx")
except FileNotFoundError:
    df = pd.DataFrame(columns=["Movie Name", "Release Year", "Rating (1-5)"])

# Create the main window
root = tk.Tk()
root.title("Movie Data Entry")

# Prompt user for movie name, release year, and rating
movie_name = simpledialog.askstring("Input", "Enter the movie name:", parent=root)
release_year = simpledialog.askinteger("Input", "Enter the release year:", parent=root)
rating = simpledialog.askfloat("Input", "Enter the rating (1-5):", parent=root)

# Check if the user didn't cancel the dialogs
if all([movie_name, release_year, rating]):
    add_data(movie_name, release_year, rating)

root.mainloop()
