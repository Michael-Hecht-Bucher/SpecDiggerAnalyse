# SpecDiggerAnalyse
A GUI-based nativeMS data analysis software for automated species quantification, data visualization and statistics based on raw peak areas

<img width="880" height="730" alt="image" src="https://github.com/user-attachments/assets/2a12b615-4df5-4ca8-87a3-e88c0627b328" />

## 1. Usage 
The software is intended to be used with raw peak areas supplied in XLSX or CSV format and treats each input file as a separate measurement. 

### 1.1 Load and normalize data 
- Load input data with `Load Excel files...` and select all measurements of a given condition you want to analyse
- Normalize the data either to a selected subset of species or to all previously identified species and set the sum of their peak areas as 100% with `Normalize on all species`
- This automatically triggers data conversion to relative species abundance as well as statistical data analysis (one way ANOVA with Tukey's posthoc test) and visualization as bar graphs 

### 1.2 Customization and data export 
- Bar graphs can be customized either with `Plot settings...` or by clicking on the customization icon directly in the plot-window.
- Visualized data can be exported with `Export plots...` either as image or in vector format (e.g. SVG)
- Numerical data can be exported either with `Export XLSX...` for native Excel-format or with `Export CSV...` for CSV-format. 
