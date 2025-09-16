# Shortcut script to activate venv and run Streamlit dashboard

# Allow running scripts (safe for current user only)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force

# Activate virtual environment
. .\.venv\Scripts\Activate

# Launch Streamlit dashboard
streamlit run dashboard.py
# To stop the dashboard, press Ctrl+C in this terminal
# To deactivate the virtual environment, run `deactivate`
#PS C:\Users\ADMIN\Desktop\Collections Dashboard> .\activate.ps1 to run the dashboard
