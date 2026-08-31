# Power BI Setup

## Open the dashboard

Open:

`dashboards/powerbi/Automated_Bank_Reconciliation_Dashboard.pbix`

## Local data source

The Power BI dashboard uses the generated reconciliation output:

`data/output/reconciliation_results.csv`

If Power BI asks for the file location, select the `reconciliation_results.csv` file from the project's `data/output` folder.

## Refresh the dashboard

After generating a new reconciliation result:

1. Run `scripts\refresh_all.ps1`.
2. Open the Power BI `.pbix` file.
3. Select **Refresh** in Power BI Desktop.
4. Verify that the visuals reflect the latest reconciliation output.

## Power BI Service

To publish the dashboard:

1. Open the `.pbix` file in Power BI Desktop.
2. Sign in to your Power BI account.
3. Select **Publish**.
4. Choose the appropriate workspace.
5. Configure the dataset/data source credentials in Power BI Service if required.
6. Configure scheduled refresh if the environment supports it.

## Important

The repository does not contain Power BI credentials, access tokens, or other secrets.

Power BI local configuration files and credentials should not be committed to GitHub.
