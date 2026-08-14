"""
A script to generate a PDF from a YAML file, structured as a Cyber Assessment Framework.

The program reads a YAML file containing objectives, principles, outcomes, and indicators,
and generates a styled PDF report summarizing this hierarchical data. The generated PDF
includes sections for objectives and their corresponding components, such as principles,
outcomes, and indicators, styled for clarity and organization.

Functions:
    - generate_pdf(): Handles the workflow of reading the YAML file, parsing its data,
      generating formatted HTML content, and exporting it as a PDF file.
"""

import yaml
from weasyprint import HTML


def generate_pdf():
    yaml_path = "cyber-assessment-framework-v4.0.yaml"
    output_path = "cyber-assessment-framework-v4.0.pdf"

    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    objectives = data.get("objectives", {})

    html_content = """
    <html>
    <head>
        <style>
            @page {
                margin: 2cm;
                @bottom-right {
                    content: "Page " counter(page) " of " counter(pages);
                    font-size: 10pt;
                }
            }
            body { font-family: "Helvetica", "Arial", sans-serif; color: #333; line-height: 1.5; }
            h1 { color: #005ea5; font-size: 28pt; border-bottom: 3px solid #005ea5; padding-bottom: 10px; margin-bottom: 40px; }
            h2 { color: #005ea5; font-size: 22pt; margin-top: 40px; page-break-before: always; border-bottom: 1px solid #bfc1c3; padding-bottom: 5px; }
            h3 { color: #0b0c0c; font-size: 18pt; margin-top: 30px; text-decoration: underline; }
            h4 { color: #0b0c0c; font-size: 16pt; margin-top: 25px; background-color: #f3f2f1; padding: 5px 10px; border-left: 5px solid #005ea5; }
            h5 { color: #0b0c0c; font-size: 14pt; margin-top: 20px; padding-left: 10px; border-left: 2px solid #505a5f; }
            p { margin-bottom: 15px; }
            .indicator-section { margin-left: 30px; margin-top: 15px; background-color: #fafafa; padding: 10px; border: 1px solid #bfc1c3; }
            .indicator-title { font-weight: bold; font-size: 12pt; display: block; margin-bottom: 10px; color: #0b0c0c; }
            .indicator-type { font-weight: bold; text-transform: uppercase; font-size: 9pt; color: #505a5f; margin-top: 15px; margin-bottom: 5px; border-bottom: 1px solid #dee0e2; }
            .indicator-item { margin-bottom: 8px; font-size: 11pt; display: flex; align-items: flex-start; }
            .code { font-weight: bold; color: #005ea5; min-width: 60px; display: inline-block; }
            .description { display: inline-block; }
        </style>
    </head>
    <body>
        <h1>Cyber Assessment Framework v4.0</h1>
        <p>Structure: Objectives &rarr; Objective &rarr; Outcomes &rarr; Outcome &rarr; Indicators</p>
    """

    for obj_code, objective in objectives.items():
        html_content += f"<h2>Objective {obj_code}: {objective.get('title', '')}</h2>"
        html_content += f"<p>{objective.get('description', '')}</p>"

        principles = objective.get("principles", {})
        if principles:
            for prin_code, principle in principles.items():
                # Level 3: Outcomes (mapped to CAF Principles)
                html_content += f"<h3>Outcomes {prin_code}: {principle.get('title', '')}</h3>"
                html_content += f"<p>{principle.get('description', '')}</p>"

                outcomes = principle.get("outcomes", {})
                for out_code, outcome in outcomes.items():
                    # Level 4: Outcome (mapped to CAF Outcomes)
                    html_content += f"<h4>Outcome {out_code}: {outcome.get('title', '')}</h4>"
                    html_content += f"<p>{outcome.get('description', '')}</p>"

                    # Level 5: Indicators (mapped to CAF IGPs)
                    indicators = outcome.get("indicators", {})
                    if indicators:
                        html_content += "<div class='indicator-section'>"
                        html_content += "<span class='indicator-title'>Indicators</span>"
                        # Order: achieved, partially-achieved, not-achieved
                        for status in ["achieved", "partially-achieved", "not-achieved"]:
                            items = indicators.get(status, {})
                            if items:
                                html_content += f"<div class='indicator-type'>{status.replace('-', ' ')}</div>"
                                for ind_code, indicator in items.items():
                                    desc = indicator.get("description", "")
                                    html_content += f"<div class='indicator-item'><span class='code'>{ind_code}</span> <span class='description'>{desc}</span></div>"
                        html_content += "</div>"

    html_content += """
    </body>
    </html>
    """

    HTML(string=html_content).write_pdf(output_path)
    print(f"PDF generated successfully at {output_path}")


if __name__ == "__main__":
    generate_pdf()
