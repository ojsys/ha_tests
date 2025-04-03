from django import forms
import pandas as pd
from io import StringIO
from .models import Test

class QuestionUploadForm(forms.Form):
    file = forms.FileField(
        label='Select a file',
        help_text='Accepted formats: CSV, Excel (.xlsx, .xls)'
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file extension
            if not (file.name.endswith('.csv') or file.name.endswith('.xlsx') or file.name.endswith('.xls')):
                raise forms.ValidationError("Unsupported file format. Please upload CSV or Excel file.")
            
            # Basic validation of file contents
            try:
                if file.name.endswith('.csv'):
                    # Read CSV
                    file_data = file.read().decode('utf-8')
                    df = pd.read_csv(StringIO(file_data))
                    file.seek(0)  # Reset file pointer
                else:
                    # Read Excel
                    df = pd.read_excel(file)
                    file.seek(0)  # Reset file pointer
                
                # Check required columns
                if 'question_text' not in df.columns:
                    raise forms.ValidationError("File must contain a 'question_text' column.")
                
                # Check MCQ questions have required columns
                for idx, row in df.iterrows():
                    q_type = row.get('question_type', 'MCQ')
                    if q_type == 'MCQ':
                        required_cols = ['option_a', 'option_b', 'option_c', 'option_d', 'correct_answer']
                        missing = [col for col in required_cols if col not in df.columns]
                        if missing:
                            raise forms.ValidationError(f"MCQ questions require columns: {', '.join(missing)}")
                        
                        # Validate correct_answer is A, B, C, or D
                        if row['correct_answer'] not in ['A', 'B', 'C', 'D']:
                            raise forms.ValidationError(f"Row {idx+1}: correct_answer must be A, B, C, or D")
                
            except Exception as e:
                raise forms.ValidationError(f"Error processing file: {str(e)}")
                
        return file

# Add the missing TestForm class
# Make sure this form exists in your forms.py
class TestForm(forms.ModelForm):
    class Meta:
        model = Test
        fields = ['title', 'description', 'duration_minutes', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
        }