# Workshop 3: Evaluating LLM Responses

### 🛠️ **What to Do**

- Pick a few LinkedIn profiles to test against
- Run your app and log the LLM outputs
- Create a CSV or spreadsheet for annotation (input, output, your labels)
- Write code to:
    - Load annotated data
    - Compute accuracy, precision, recall, confusion matrix
    - Display false positives/negatives
- Use an **LLM-as-a-judge** to replicate your human annotations and compare
- Try swapping in a different model and running the same evaluation process
- As you scale your evaluation, keep in mind:
    - Start small with clear human annotations
    - Scale gradually—only introduce LLM judgments when you understand the failure modes
    - Calibrate continuously—compare LLM outputs to your own annotations


For this approach we will be using the "Generate Email" task.

Taking the LinkedIn profile as input, the task is to generate a short email to the candidate.

1. Use the app_pdf_profile.py script to generate the LLM outputs.

```bash
python app_pdf_profile.py
```

This opens the app in the browser and you can generate the LLM outputs.

2. Download the LLM outputs from the database as json file in the test_answer.json

3. Use the streamlit app to build the annotation interface.

```bash
streamlit run eval_interface.py
```
This step creates the email_evaluations.csv file after reviewing the LLM outputs.

4. Open the evals_pdf_profile.ipynb notebook to compute the accuracy, precision, recall, confusion matrix.

Build the judge and choose the criteria for the evaluation.

In my case I used the following criteria:

- The email is relevant to the candidate's profile.
- The email is personalized to the candidate.
- The email is clear and concise.
- The email is professional and appropriate.

5. Use the LLM-as-a-judge to replicate your human annotations and compare.

My failure modes by manual reviwing was at the extraction of the details from the profile. To build a Judge that address this failure mode you need to pass the profile as context to the judge to evaluate your application effectively.