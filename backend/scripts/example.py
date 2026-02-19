import openviking as ov

# Initialize OpenViking client with data directory
client = ov.SyncOpenViking(path="./data_")

try:
    # Initialize the client
    client.initialize()

    # Add resource (supports URL, file, or directory)
    add_result = client.add_resource(
        path="https://raw.githubusercontent.com/volcengine/OpenViking/refs/heads/main/README.md"
    )
    root_uri = add_result['root_uri']

    # Explore the resource tree structure
    ls_result = client.ls(root_uri)
    print(f"Directory structure:\n{ls_result}\n")

    # Use glob to find markdown files
    glob_result = client.glob(pattern="**/*.md", uri=root_uri)
    if glob_result['matches']:
        content = client.read(glob_result['matches'][0])
        print(f"Content preview: {content[:200]}...\n")

    # Wait for semantic processing to complete
    print("Wait for semantic processing...")
    status = client.wait_processed()
    for name, s in status.items():
        if s.get("error_count", 0) > 0:
            print(f"  Warning: queue {name} had {s['error_count']} error(s): {s.get('errors', [])}")

    # Get abstract and overview (may be missing if semantic processing failed)
    try:
        abstract = client.abstract(root_uri)
        overview = client.overview(root_uri)
        print(f"Abstract:\n{abstract}\n\nOverview:\n{overview}\n")
    except Exception as e:
        if "no such file" in str(e).lower() or ".abstract.md" in str(e):
            print("  Abstract/overview not available (semantic processing may have failed for this resource).")
        else:
            raise

    # Perform semantic search
    results = client.find("what is openviking", target_uri=root_uri)
    print("Search results:")
    for r in results.resources:
        print(f"  {r.uri} (score: {r.score:.4f})")

    # Close the client
    client.close()

except Exception as e:
    print(f"Error: {e}")