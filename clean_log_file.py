def clean_log_file():
    with open("data/message_logs.ndjson", "r") as file:
        lines = file.readlines()

    with open("data/message_logs.ndjson", "w") as file:
        for line in lines:
            if line.strip():  # Only write non-empty lines
                file.write(line)


# Run the script to clean the log file
clean_log_file()
