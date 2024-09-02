import tkinter as tk

def submit_text():
    # Get the text from the entry widget
    user_input = text_entry.get()
    
    # Display the text on the label
    output_label.config(text=f"You entered: {user_input}")

    # Clear the text entry
    text_entry.delete(0, tk.END)

# Create the main window
root = tk.Tk()
root.title("Simple Text Input")

# Create a label to prompt the user
prompt_label = tk.Label(root, text="Enter some text:")
prompt_label.pack(pady=10)

# Create a text entry widget
text_entry = tk.Entry(root, width=40)
text_entry.pack(pady=5)

# Create a button to submit the text
submit_button = tk.Button(root, text="Submit", command=submit_text)
submit_button.pack(pady=10)

# Create a label to display the output
output_label = tk.Label(root, text="")
output_label.pack(pady=20)

# Start the main loop
root.mainloop()
