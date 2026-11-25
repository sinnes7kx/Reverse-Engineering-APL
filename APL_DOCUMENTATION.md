# Reverse Engineer a Result — APL Project 2026

## Goal
Recreate an existing application using generative AI by working backwards from its visible results and understanding how it might work.

## Step 1 – Look at the application

**What does the application do?**

The application displays flight information from different airports. It allows the user to search for flights and view arrivals and departures through a terminal interface.

## Step 2 – Ask questions

**What kind of data is this?**

It is structured flight information, such as flight numbers, destinations, departure times and arrival times. The information can be represented in JSON format.

**What could have created this?**

A program written in Python could retrieve information from an API, process the data and display the results in a readable format.

**How can generative AI help?**

Generative AI can help explain the data, suggest how the application might work, generate example code and assist with troubleshooting.

## Step 3 – Guess the inputs

**What inputs would you need to get this result?**

The application would need information such as an airport, a date and whether the user wants to see arrivals or departures. It may also need an API key to retrieve live information.

## Step 4 – Guess the process

**What functions or logic might build this?**

1. The user enters or selects information.
2. The application checks the input.
3. Information is requested from an API.
4. The returned data is processed and filtered.
5. The results are displayed to the user.

This is a possible explanation of how the original application works, rather than a confirmed description of its source code.

## Step 5 – Sketch the steps

**What might a function look like?**

```python
def show_flights(airport, date, direction):
    # Retrieve flight information
    # Filter the results
    # Display the information
    pass
```

This is a simplified example of the logic behind the application.

## Step 6 – Try building it

**Can you make an application that gives similar output?**

Yes. A similar application has been recreated in Python with the assistance of generative AI. It retrieves or uses demonstration flight data and presents the results in a terminal.

The reconstructed application can be tested to check whether its functions behave as expected.

## Results and conclusion

The project demonstrates how an application can be reconstructed by observing its output, identifying possible inputs and understanding the logic behind the results.

All 33 automated tests passed on 25 November 2026. Live API access was not retested during the documentation update, and exact equivalence to the original application has not been established.

Generative AI is a useful tool for understanding and recreating software, but the generated code still needs to be reviewed and tested.

## Security

API keys and other private credentials should not be uploaded to GitHub.
