#!/usr/bin/env python

"""
Report generator for Teatime test results
Generates HTML reports from test JSON results
"""

import os
import json
import argparse
from datetime import datetime
from pathlib import Path
import shutil

def generate_report(test_output_dir, output_file=None):
    """
    Generate an HTML report from test results
    
    Args:
        test_output_dir: Path to test output directory
        output_file: Output HTML file (defaults to index.html in test directory)
    """
    if not output_file:
        output_file = os.path.join(test_output_dir, "index.html")
        
    # Load results.json
    results_file = os.path.join(test_output_dir, "results.json")
    if not os.path.exists(results_file):
        print(f"Error: Results file not found: {results_file}")
        return False
        
    with open(results_file, "r") as f:
        results = json.load(f)
        
    # Basic test info
    test_name = results.get("test_name", "Unknown Test")
    start_time = results.get("start_time", "")
    end_time = results.get("end_time", "")
    success = results.get("success", False)
    
    # Calculate duration if possible
    duration = ""
    if start_time and end_time:
        try:
            start = datetime.fromisoformat(start_time)
            end = datetime.fromisoformat(end_time)
            duration = str(end - start)
        except:
            duration = "Unknown"
            
    # Get steps, errors, screenshots
    steps = results.get("steps", [])
    errors = results.get("errors", [])
    screenshots = results.get("screenshots", [])
    
    # Generate HTML
    html = generate_html_report(
        test_name=test_name,
        start_time=start_time,
        end_time=end_time,
        duration=duration,
        success=success,
        steps=steps,
        errors=errors,
        screenshots=screenshots,
        test_dir=test_output_dir
    )
    
    # Write HTML to file
    with open(output_file, "w") as f:
        f.write(html)
        
    print(f"Report generated: {output_file}")
    return True

def generate_html_report(test_name, start_time, end_time, duration, success, steps, errors, screenshots, test_dir):
    """Generate HTML report content"""
    
    # Format timestamps
    try:
        start_formatted = datetime.fromisoformat(start_time).strftime("%Y-%m-%d %H:%M:%S")
    except:
        start_formatted = start_time
        
    try:
        end_formatted = datetime.fromisoformat(end_time).strftime("%Y-%m-%d %H:%M:%S")
    except:
        end_formatted = end_time
        
    # Count step statuses
    step_statuses = {"success": 0, "failed": 0, "warning": 0, "running": 0}
    for step in steps:
        status = step.get("status", "")
        step_statuses[status] = step_statuses.get(status, 0) + 1
        
    # Create screenshots gallery
    screenshots_html = ""
    for i, screenshot in enumerate(screenshots):
        if not os.path.exists(screenshot):
            continue
            
        # Get relative path to screenshot from test directory
        rel_path = os.path.relpath(screenshot, test_dir)
        
        # Create thumbnail in screenshots_thumb directory
        thumb_dir = os.path.join(test_dir, "screenshots_thumb")
        os.makedirs(thumb_dir, exist_ok=True)
        
        thumb_name = f"thumb_{os.path.basename(screenshot)}"
        thumb_path = os.path.join(thumb_dir, thumb_name)
        
        # Note: We're not actually creating thumbnails here, just using the same images
        # In a real implementation, you might want to generate actual thumbnails
        if not os.path.exists(thumb_path):
            shutil.copy(screenshot, thumb_path)
            
        thumb_rel_path = os.path.join("screenshots_thumb", thumb_name)
        
        # Add to gallery
        filename = os.path.basename(screenshot)
        screenshots_html += f"""
            <div class="screenshot">
                <a href="{rel_path}" target="_blank">
                    <img src="{thumb_rel_path}" alt="{filename}" />
                </a>
                <div class="caption">{filename}</div>
            </div>
        """
        
    # Create steps table
    steps_html = ""
    for step in steps:
        step_id = step.get("id", "")
        description = step.get("description", "")
        start = step.get("start_time", "")
        end = step.get("end_time", "")
        status = step.get("status", "")
        data = step.get("data", {})
        
        # Format timestamps
        try:
            start_formatted = datetime.fromisoformat(start).strftime("%H:%M:%S")
        except:
            start_formatted = start
            
        try:
            end_formatted = datetime.fromisoformat(end).strftime("%H:%M:%S")
        except:
            end_formatted = end
            
        # Format step duration
        step_duration = ""
        if start and end:
            try:
                s = datetime.fromisoformat(start)
                e = datetime.fromisoformat(end)
                step_duration = str(e - s)
            except:
                step_duration = "Unknown"
                
        # Format status with color
        status_class = {
            "success": "success",
            "failed": "danger",
            "warning": "warning",
            "running": "info"
        }.get(status, "")
        
        # Format data as JSON
        data_formatted = json.dumps(data, indent=2) if data else ""
        
        steps_html += f"""
            <tr class="{status_class}">
                <td>{step_id}</td>
                <td>{description}</td>
                <td>{status}</td>
                <td>{start_formatted}</td>
                <td>{step_duration}</td>
                <td>
                    <button class="btn btn-sm btn-info" type="button" 
                            data-bs-toggle="collapse" data-bs-target="#data_{step_id}" 
                            aria-expanded="false">
                        View Data
                    </button>
                    <div class="collapse" id="data_{step_id}">
                        <div class="card card-body">
                            <pre>{data_formatted}</pre>
                        </div>
                    </div>
                </td>
            </tr>
        """
        
    # Create errors list
    errors_html = ""
    if errors:
        for error in errors:
            step_id = error.get("step_id", "")
            message = error.get("message", "")
            time = error.get("time", "")
            
            # Format timestamp
            try:
                time_formatted = datetime.fromisoformat(time).strftime("%H:%M:%S")
            except:
                time_formatted = time
                
            errors_html += f"""
                <div class="alert alert-danger">
                    <strong>Error in step {step_id} at {time_formatted}:</strong> {message}
                </div>
            """
    
    # Generate full HTML
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Test Report: {test_name}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ padding: 20px; }}
            .header {{ margin-bottom: 30px; }}
            .summary {{ margin-bottom: 30px; }}
            .steps {{ margin-bottom: 30px; }}
            .screenshots {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 30px; }}
            .screenshot {{ width: 200px; text-align: center; }}
            .screenshot img {{ max-width: 100%; border: 1px solid #ddd; }}
            .caption {{ font-size: 0.8rem; margin-top: 5px; }}
            .success {{ background-color: #d4edda; }}
            .danger {{ background-color: #f8d7da; }}
            .warning {{ background-color: #fff3cd; }}
            .info {{ background-color: #d1ecf1; }}
            pre {{ white-space: pre-wrap; }}
        </style>
    </head>
    <body>
        <div class="container-fluid">
            <div class="header">
                <h1>{test_name} Report</h1>
                <div class="badge bg-{'success' if success else 'danger'} fs-5">
                    {'SUCCESS' if success else 'FAILED'}
                </div>
            </div>
            
            <div class="summary card">
                <div class="card-header">
                    <h2>Test Summary</h2>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <p><strong>Start Time:</strong> {start_formatted}</p>
                            <p><strong>End Time:</strong> {end_formatted}</p>
                            <p><strong>Duration:</strong> {duration}</p>
                            <p><strong>Steps:</strong> {len(steps)}</p>
                            <p><strong>Successful Steps:</strong> {step_statuses.get('success', 0)}</p>
                            <p><strong>Failed Steps:</strong> {step_statuses.get('failed', 0)}</p>
                        </div>
                        <div class="col-md-6">
                            <p><strong>Warnings:</strong> {step_statuses.get('warning', 0)}</p>
                            <p><strong>Errors:</strong> {len(errors)}</p>
                            <p><strong>Screenshots:</strong> {len(screenshots)}</p>
                        </div>
                    </div>
                </div>
            </div>
            
            {f'<div class="errors">{errors_html}</div>' if errors else ''}
            
            <div class="steps card">
                <div class="card-header">
                    <h2>Test Steps</h2>
                </div>
                <div class="card-body">
                    <table class="table table-bordered">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Description</th>
                                <th>Status</th>
                                <th>Start Time</th>
                                <th>Duration</th>
                                <th>Data</th>
                            </tr>
                        </thead>
                        <tbody>
                            {steps_html}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="screenshots-section card">
                <div class="card-header">
                    <h2>Screenshots</h2>
                </div>
                <div class="card-body">
                    <div class="screenshots">
                        {screenshots_html}
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    
    return html

def find_test_directories(base_dir="artifacts/test_results"):
    """Find all test result directories"""
    if not os.path.exists(base_dir):
        return []
        
    test_dirs = []
    for entry in os.scandir(base_dir):
        if entry.is_dir():
            results_file = os.path.join(entry.path, "results.json")
            if os.path.exists(results_file):
                test_dirs.append(entry.path)
                
    # Sort by modification time (newest first)
    test_dirs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return test_dirs

def generate_index_report(base_dir="artifacts/test_results"):
    """Generate an index HTML report of all tests"""
    test_dirs = find_test_directories(base_dir)
    if not test_dirs:
        print("No test results found.")
        return False
        
    index_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Teatime Test Reports</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { padding: 20px; }
            .success { background-color: #d4edda; }
            .danger { background-color: #f8d7da; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Teatime Test Reports</h1>
            <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>Test Name</th>
                        <th>Date & Time</th>
                        <th>Result</th>
                        <th>Report</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for test_dir in test_dirs:
        results_file = os.path.join(test_dir, "results.json")
        
        with open(results_file, "r") as f:
            results = json.load(f)
            
        test_name = results.get("test_name", "Unknown Test")
        start_time = results.get("start_time", "")
        success = results.get("success", False)
        
        # Format timestamp
        try:
            start_formatted = datetime.fromisoformat(start_time).strftime("%Y-%m-%d %H:%M:%S")
        except:
            start_formatted = start_time
            
        # Ensure report exists, generate if not
        report_file = os.path.join(test_dir, "index.html")
        if not os.path.exists(report_file):
            generate_report(test_dir)
            
        # Get relative path from base_dir to report file
        rel_path = os.path.relpath(report_file, base_dir)
            
        index_html += f"""
                <tr class="{'success' if success else 'danger'}">
                    <td>{test_name}</td>
                    <td>{start_formatted}</td>
                    <td>{'SUCCESS' if success else 'FAILED'}</td>
                    <td><a href="{rel_path}" class="btn btn-sm btn-primary">View Report</a></td>
                </tr>
        """
        
    index_html += """
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    
    # Write index HTML to file
    index_file = os.path.join(base_dir, "index.html")
    with open(index_file, "w") as f:
        f.write(index_html)
        
    print(f"Index report generated: {index_file}")
    return True

def main():
    """Main entry point for report generator"""
    parser = argparse.ArgumentParser(description="Generate HTML reports from test results")
    parser.add_argument("--dir", help="Test results directory")
    parser.add_argument("--index", action="store_true", help="Generate index report")
    parser.add_argument("--all", action="store_true", help="Generate reports for all tests")
    
    args = parser.parse_args()
    
    if args.index or args.all:
        generate_index_report()
        
    if args.dir:
        generate_report(args.dir)
    elif args.all:
        test_dirs = find_test_directories()
        for test_dir in test_dirs:
            generate_report(test_dir)
            
if __name__ == "__main__":
    main()
