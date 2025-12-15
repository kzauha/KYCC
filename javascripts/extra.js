// Custom JavaScript for KYCC documentation

document.addEventListener('DOMContentLoaded', function() {
  // Add copy button functionality enhancement
  const codeBlocks = document.querySelectorAll('pre code');
  
  codeBlocks.forEach(function(codeBlock) {
    codeBlock.addEventListener('copy', function() {
      // Show a toast notification (if you want to add custom feedback)
      console.log('Code copied to clipboard!');
    });
  });

  // Highlight API methods in content
  const content = document.querySelector('.md-content');
  if (content) {
    // GET
    content.innerHTML = content.innerHTML.replace(
      /\bGET\s+\//g, 
      '<span class="api-method get">GET</span> /'
    );
    
    // POST
    content.innerHTML = content.innerHTML.replace(
      /\bPOST\s+\//g, 
      '<span class="api-method post">POST</span> /'
    );
    
    // PUT
    content.innerHTML = content.innerHTML.replace(
      /\bPUT\s+\//g, 
      '<span class="api-method put">PUT</span> /'
    );
    
    // DELETE
    content.innerHTML = content.innerHTML.replace(
      /\bDELETE\s+\//g, 
      '<span class="api-method delete">DELETE</span> /'
    );
  }

  // Auto-scroll to heading on page load if hash is present
  if (window.location.hash) {
    setTimeout(function() {
      const element = document.querySelector(window.location.hash);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 100);
  }
});

// Add keyboard shortcuts
document.addEventListener('keydown', function(e) {
  // Ctrl/Cmd + K: Focus search
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    const searchInput = document.querySelector('.md-search__input');
    if (searchInput) {
      searchInput.focus();
    }
  }
});
