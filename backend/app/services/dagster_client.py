"""
Dagster GraphQL Client for triggering pipeline runs.

This module allows the backend API to communicate with the Dagster webserver
running in a separate container via its GraphQL API.
"""
import os
import json
import logging
import requests
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Dagster GraphQL endpoint (in Docker network, dagster container is accessible by service name)
DAGSTER_GRAPHQL_URL = os.getenv("DAGSTER_GRAPHQL_URL", "http://dagster:3000/graphql")


class DagsterClient:
    """Client for Dagster GraphQL API."""
    
    def __init__(self, graphql_url: str = None):
        self.graphql_url = graphql_url or DAGSTER_GRAPHQL_URL
    
    def launch_run(
        self,
        job_name: str,
        run_config: Dict[str, Any],
        repository_name: str = "__repository__",
        location_name: str = "definitions.py"
    ) -> Dict[str, Any]:
        """
        Launch a Dagster job run via GraphQL.
        
        Args:
            job_name: Name of the job to run (e.g., "unified_training_job")
            run_config: Run configuration dict
            repository_name: Repository name (usually "__repository__" for modern Dagster)
            location_name: Code location name 
            
        Returns:
            Dict with run_id and launch status
        """
        # GraphQL mutation to launch a run
        mutation = """
        mutation LaunchRun($executionParams: ExecutionParams!) {
            launchRun(executionParams: $executionParams) {
                __typename
                ... on LaunchRunSuccess {
                    run {
                        runId
                        status
                    }
                }
                ... on PythonError {
                    message
                    stack
                }
                ... on InvalidSubsetError {
                    message
                }
                ... on InvalidOutputError {
                    invalidOutputName
                    stepKey
                }
            }
        }
        """
        
        variables = {
            "executionParams": {
                "selector": {
                    "repositoryName": repository_name,
                    "repositoryLocationName": location_name,
                    "jobName": job_name
                },
                "runConfigData": run_config
            }
        }
        
        try:
            response = requests.post(
                self.graphql_url,
                json={"query": mutation, "variables": variables},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Check for GraphQL errors
            if "errors" in result:
                error_msg = result["errors"][0].get("message", "Unknown GraphQL error")
                logger.error(f"Dagster GraphQL error: {error_msg}")
                return {"success": False, "error": error_msg}
            
            launch_result = result.get("data", {}).get("launchRun", {})
            
            if launch_result.get("__typename") == "LaunchRunSuccess":
                run_info = launch_result.get("run", {})
                return {
                    "success": True,
                    "run_id": run_info.get("runId"),
                    "status": run_info.get("status")
                }
            elif launch_result.get("__typename") == "PythonError":
                error_msg = f"PythonError: {launch_result.get('message')} \nStack: {launch_result.get('stack')}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
            elif launch_result.get("__typename") == "InvalidOutputError":
                 error_msg = f"InvalidOutputError: Output '{launch_result.get('invalidOutputName')}' from step '{launch_result.get('stepKey')}'"
                 logger.error(error_msg)
                 return {"success": False, "error": error_msg}
            else:
                typename = launch_result.get("__typename", "Unknown")
                error_msg = launch_result.get("message", f"Launch failed (Type: {typename})")
                logger.error(f"Dagster launch failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Cannot connect to Dagster at {self.graphql_url}: {e}")
            return {"success": False, "error": f"Cannot connect to Dagster: {e}"}
        except Exception as e:
            logger.error(f"Dagster client error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_run_status(self, run_id: str) -> Dict[str, Any]:
        """Get the status of a Dagster run."""
        query = """
        query RunStatus($runId: ID!) {
            runOrError(runId: $runId) {
                __typename
                ... on Run {
                    runId
                    status
                    startTime
                    endTime
                }
                ... on RunNotFoundError {
                    message
                }
            }
        }
        """
        
        try:
            response = requests.post(
                self.graphql_url,
                json={"query": query, "variables": {"runId": run_id}},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            run_result = result.get("data", {}).get("runOrError", {})
            
            if run_result.get("__typename") == "Run":
                return {
                    "success": True,
                    "run_id": run_result.get("runId"),
                    "status": run_result.get("status"),
                    "start_time": run_result.get("startTime"),
                    "end_time": run_result.get("endTime")
                }
            else:
                return {"success": False, "error": run_result.get("message", "Run not found")}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def health_check(self) -> bool:
        """Check if Dagster is reachable."""
        try:
            response = requests.post(
                self.graphql_url,
                json={"query": "{ __typename }"},
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False


# Singleton instance
_client: Optional[DagsterClient] = None


def get_dagster_client() -> DagsterClient:
    """Get the Dagster client singleton."""
    global _client
    if _client is None:
        _client = DagsterClient()
    return _client
