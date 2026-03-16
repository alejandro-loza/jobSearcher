import json
import time
from loguru import logger
from src.tools import jobspy_tool
from src.agents import master_agent
from src.db.tracker import JobTracker

def run_targeted_search():
    logger.info("Starting targeted job search for Java/Spring Boot SR roles...")
    
    # Load resume for evaluation
    try:
        with open('data/resume.json', 'r') as f:
            resume = json.load(f)
    except Exception as e:
        logger.error(f"Could not load resume: {e}")
        return

    tracker = JobTracker()
    
    # Specific companies requested
    target_companies = ["Globant", "EPAM", "Luxoft"]
    
    # 1. Search specific companies directly in the search term
    # JobSpy works best with broader terms, but we can try appending the company name or searching broadly and filtering
    
    queries = [
        "Senior Java Developer Globant",
        "Senior Java Developer EPAM",
        "Senior Java Developer Luxoft",
        "Senior Java Spring Boot",
        "Senior Groovy Developer"
    ]
    
    location = "Mexico"
    all_jobs = []
    
    for q in queries:
        logger.info(f"Querying: {q} en {location}")
        jobs = jobspy_tool.search_jobs(
            search_term=q,
            location=location,
            results_wanted=15,
            hours_old=336, # Last 14 days
            site_names=["linkedin"],
            easy_apply_only=False
        )
        all_jobs.extend(jobs)
        time.sleep(3) # Anti-rate limit
        
    # Deduplicate jobs by ID
    unique_jobs = {j["id"]: j for j in all_jobs}.values()
    logger.info(f"Total unique jobs found: {len(unique_jobs)}")
    
    # Filter for relevant companies and roles
    # The user asked for Globant, EPAM, Luxoft AND best companies in Mexico
    # We will evaluate all of them, but highlight the requested ones.
    
    high_match_jobs = []
    
    for job in unique_jobs:
        company_name = job.get('company', '').lower()
        title = job.get('title', '').lower()
        
        # Fast pre-filter to drop obviously irrelevant ones
        if not any(kw in title for kw in ['java', 'spring', 'backend', 'back end', 'software', 'engineer', 'developer']):
            continue
            
        # We only evaluate if it seems relevant or if it belongs to target companies
        is_target_company = any(c.lower() in company_name for c in target_companies)
        
        # Evaluate job match
        logger.info(f"Evaluating {job['title']} at {job['company']}...")
        score, reasons = master_agent.evaluate_job_match(job, resume)
        
        if score >= 75 or is_target_company:
            job['match_score'] = score
            job['evaluation_reasons'] = reasons
            high_match_jobs.append(job)
            
            # Save to DB so it appears in the dashboard
            tracker.save_job(job)
            tracker.update_job_status(job['id'], 'found')
            
    # Print report
    logger.info("\n=== TARGETED SEARCH REPORT ===")
    
    # Sort by score descending
    high_match_jobs.sort(key=lambda x: x.get('match_score', 0), reverse=True)
    
    for j in high_match_jobs:
        company = j.get('company', 'Unknown')
        title = j.get('title', 'Unknown')
        score = j.get('match_score', 0)
        marker = "⭐ TARGET" if any(c.lower() in company.lower() for c in target_companies) else ""
        print(f"[{score}/100] {title} @ {company} {marker}")
        print(f"  URL: {j.get('url', 'N/A')}")
        print(f"  Location: {j.get('location', 'N/A')} - Remote: {j.get('easy_apply', False)}")
        print(f"  Reason: {j.get('evaluation_reasons', '')[:100]}...")
        print()

if __name__ == "__main__":
    run_targeted_search()
