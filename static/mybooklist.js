document.addEventListener('DOMContentLoaded', () => {
  const userId = document.getElementById('userIdDisplay').textContent.trim();
  const bookListContainer = document.getElementById('myBookListResults');
  const recommendationResults = document.getElementById('recommendationResults');
  const pageInfo = document.getElementById('pageInfo');
  const prevPageBtn = document.getElementById('prevPage');
  const nextPageBtn = document.getElementById('nextPage');
  const getRecommendationsBtn = document.getElementById('getRecommendationsBtn');
  const loadingRing = document.getElementById('loadingRing');

  let currentPage = 1;
  let totalPages = 1;

  // Fetch books
  function fetchBooks(page = 1) {
    fetch(`/api/user/${userId}/books?page=${page}`)
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          currentPage = data.page;
          totalPages = data.total_pages;
          renderBooks(data.books);
          updatePagination();
        } else {
          showMessage(bookListContainer, data.message || "Failed to load books.");
        }
      })
      .catch(err => {
        showMessage(bookListContainer, `Error: ${err}`);
      });
  }

  // Render books
  function renderBooks(books) {
    if (books.length === 0) {
      showMessage(bookListContainer, "No books found.");
      return;
    }

    const cards = books.map(book => `
      <div class="book-card card">
        <img src="${book.image}" alt="${book.title}">
        <div class="book-info">
          <h3 title="${book.title}">${book.title}</h3>
          <div class="book-author text-muted font-sm">${book.author}</div>
          <div class="book-isbn font-sm">ISBN: ${book.isbn}</div>
          <div class="book-rating font-sm">Rating: ${book.rating} / 10</div>
        </div>
      </div>
    `).join('');

    bookListContainer.innerHTML = cards;
  }

  // Update pagination
  function updatePagination() {
    pageInfo.textContent = `Page ${currentPage} / ${totalPages}`;
    prevPageBtn.disabled = currentPage <= 1;
    nextPageBtn.disabled = currentPage >= totalPages;
  }

 function fetchRecommendations() {
    console.log("Fetching recommendations...");
    loadingRing.style.display = 'flex';
    
    fetch(`/api/user/${userId}/hybrid-recommend`)
        .then(res => {
            console.log("Response status:", res.status);
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            return res.json();
        })
        .then(data => {
            console.log("Recommendation data:", data);
            if (data.success) {
                renderRecommendations(data.recommendations || []);
            } else {
                console.error("Recommendation error:", data.error);
                showMessage(recommendationResults, data.error);
            }
        })
        .catch(err => {
            console.error("Fetch error:", err);
            showMessage(recommendationResults, "Error: " + err.message);
        })
        .finally(() => {
            loadingRing.style.display = 'none';
        });
}
 
// Render recommendation cards with detailed explanations
function renderRecommendations(recommendations) {
    if (recommendations.length === 0) {
        showMessage(recommendationResults, "No recommendations found.");
        return;
    }

    const cards = recommendations.map(rec => `
      <div class="recommendation-card">
        <img src="${rec.image_url || rec.image || 'placeholder.jpg'}" alt="${rec.title}">
        <div class="recommendation-info">
          <h3 title="${rec.title}">${rec.title}</h3>
          <p class="author text-muted">${rec.author}</p>
          
          <div class="score-container">
            <span class="score hybrid-score">
              ${rec.hybrid_score?.toFixed(2) || rec.predicted_score?.toFixed(2) || 'N/A'}
              <span class="score-label">Overall score</span>
            </span>
            
            <span class="score ${rec.score_type === 'user_similarity' ? 'user-sim' : 'author-sim'}">
              ${(rec.score_value * 100)?.toFixed(1) || '0'}%
              <span class="score-label">
                ${rec.score_type === 'user_similarity' ? 'User match' : 'Author match'}
              </span>
            </span>
          </div>
          
          <div class="explanation">
            <i class="fas fa-info-circle"></i>
            ${rec.explanation || 'Recommended based on your reading history'}
          </div>
        </div>
      </div>
    `).join('');

    recommendationResults.innerHTML = cards;
}
  // Display messages
  function showMessage(container, message) {
    container.innerHTML = `<div class="message-box">${message}</div>`;
  }

  // Event listeners
  prevPageBtn.addEventListener('click', () => {
    if (currentPage > 1) fetchBooks(currentPage - 1);
  });

  nextPageBtn.addEventListener('click', () => {
    if (currentPage < totalPages) fetchBooks(currentPage + 1);
  });

  getRecommendationsBtn.addEventListener('click', fetchRecommendations);

  // Back to search button
  document.getElementById('backToSearchBtn')?.addEventListener('click', () => {
    const userId = document.getElementById('userIdDisplay').textContent.trim();
    window.location.href = `/user/${userId}/service`;
  });

  // Back to main page
  document.getElementById('backBtn')?.addEventListener('click', () => {
    window.location.href = '/';
  });

  // Initial load
  fetchBooks();
});