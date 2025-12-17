import requests
import json

def query_repos():
    url = "http://localhost:3000/graphql"
    query = """
    query {
      repositoriesOrError {
        ... on RepositoryConnection {
          nodes {
            name
            location {
              name
            }
          }
        }
        ... on PythonError {
             message
        }
      }
    }
    """
    try:
        resp = requests.post(url, json={"query": query}, timeout=5)
        print(json.dumps(resp.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    query_repos()
