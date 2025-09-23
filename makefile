deploy:
	 uv run scripts/deploy_cloud_run.py	 
backend:
	uv run main.py
ui:
	uv run streamlit run streamlit_app.py
