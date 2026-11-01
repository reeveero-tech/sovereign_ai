import csv
import glob
import json
import os

import pandas as pd
import yaml


def process_benchmark_results(directory_path):
    # Get all JSON files in the directory
    json_files = glob.glob(os.path.join(directory_path, "*.json"))
    
    # Prepare CSV output
    csv_file = os.path.join(directory_path, "benchmark_stats.csv")
    
    results = []
    
    for file_path in json_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            metadata = data.get('metadata', {})
            # Get the config information
            config_file_path = metadata.get('agent_config', {})
            try:
                with open(config_file_path, 'r') as config_file:
                    config_data = yaml.safe_load(config_file)
                
                agent = config_data.get('agent', {})
                # Extract config values
                model = agent.get('model', 'unknown')
                if agent.get('type') == 'base_llm':
                    agent_type = 'base_llm'
                    model = agent.get('model', 'unknown')
                elif agent.get('type') == 'deep_researcher':
                    if '1step' in config_file_path:
                        agent_type = 'deep_researcher_1step'
                    else:
                        agent_type = 'deep_researcher_3step'
                    model = agent.get('answer_model', 'unknown')
                elif agent.get('type') == 'smolagents':
                    agent_type = 'smolagents'
                    model = agent.get('model', 'unknown')
                elif agent.get('type') == 'langchain_deep_researcher':
                    agent_type = 'langchain_deep_researcher'
                    model = agent.get('writer_model', 'unknown')
                else:
                    agent_type = 'unknown'
                    model = 'unknown'

            except Exception as e:
                print(f"Error reading config file {config_file_path}: {e}")
            
            # Process the results
            total_count = 0
            correct_count = 0
            invalid_count = 0
            
            for result in data.get('question_details', []):
                evaluation = result.get('evaluation')
                
                # Skip entries with no evaluation
                if evaluation is None:
                    continue
                
                total_count += 1
                
                # Count correct answers
                if evaluation == True:
                    correct_count += 1

                # Count invalid answers
                if str(evaluation) == '0':
                    invalid_count += 1
            
            # Calculate metrics
            overall_accuracy = correct_count / total_count if total_count > 0 else 0
            corrected_accuracy = correct_count / (total_count - invalid_count) if (total_count - invalid_count) > 0 else 0
            
            results.append({
                'agent_type': agent_type,
                'model': model,
                'valid_count': total_count - invalid_count,
                'total_count': total_count,
                'overall_accuracy': overall_accuracy,
                'corrected_accuracy': corrected_accuracy,
                'file': os.path.basename(file_path),
            })
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Sort results by agent_type and model
    results.sort(key=lambda x: (x['agent_type'], x['model']))
    
    # Write to CSV
    if results:
        fields = [
        'agent_type', 'model', 'valid_count', 'total_count',
            'overall_accuracy', 'corrected_accuracy', 'file'
        ]
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(results)
        
        print(f"Results saved to {csv_file}")
    else:
        print("No results to save")


def analyze_benchmark_results(csv_path):
    # Read the CSV file
    df = pd.read_csv(csv_path)
    
    # Group by agent_type and model, and calculate mean and std for relevant metrics
    grouped_stats = df.groupby(['agent_type', 'model']).agg({
        'valid_count': ['mean', 'std'],
        'total_count': ['mean', 'std'],
        'overall_accuracy': ['mean', 'std'],
        'corrected_accuracy': ['mean', 'std']
    }).reset_index()
    
    # Flatten the multi-level column names
    grouped_stats.columns = [
        '_'.join(col).strip('_') for col in grouped_stats.columns.values
    ]
    
    # Create output file path
    directory = os.path.dirname(csv_path)
    output_path = os.path.join(directory, "benchmark_summary.csv")
    
    # Write to CSV
    grouped_stats.to_csv(output_path, index=False)
    print(f"Statistics saved to {output_path}")
    
    # Print the summary for quick review
    print("\nSummary Statistics:")
    for _, row in grouped_stats.iterrows():
        print(f"\nAgent Type: {row['agent_type']}")
        print(f"Model: {row['model']}")
        print(f"Overall Accuracy: {row['overall_accuracy_mean']:.4f} ± {row['overall_accuracy_std']:.4f}")
        print(f"Corrected Accuracy: {row['corrected_accuracy_mean']:.4f} ± {row['corrected_accuracy_std']:.4f}")
        print(f"Valid Count: {row['valid_count_mean']:.1f} ± {row['valid_count_std']:.1f}")
        print("-" * 50)
    
    return grouped_stats


if __name__ == "__main__":
    directory_path = "./benchmark_results"
    process_benchmark_results(directory_path)
    analyze_benchmark_results(os.path.join(directory_path, "benchmark_stats.csv"))
