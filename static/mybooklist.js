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
            renderRecommendations(data); // Burada düzeltildi
        })
        .catch(err => {
            console.error("Fetch error:", err);
            showMessage(recommendationResults, "Error: " + err.message);
        })
        .finally(() => {
            loadingRing.style.display = 'none';
        });
}


function renderRecommendations(data) {
    const container = document.getElementById("recommendationResults");
    container.innerHTML = "";

    if (!data || !data.recommendations || data.recommendations.length === 0) {
        showMessage(container, "No recommendations available.");
        return;
    }

    data.recommendations.forEach(rec => {
        const card = document.createElement("div");
        card.className = "recommendation-card";

        const img = document.createElement("img");
        img.src = rec.image_url || "default.jpg";
        img.alt = rec.title;

        const info = document.createElement("div");
        info.className = "recommendation-info";

        const title = document.createElement("h3");
        title.textContent = rec.title;

        const author = document.createElement("div");
        author.className = "author";
        author.textContent = rec.author;

        const scoreContainer = document.createElement("div");
        scoreContainer.className = "score-container";

        const score = document.createElement("span");
        score.className = "score hybrid-score";
        score.textContent = `Hybrid Score: ${(rec.hybrid_score * 100).toFixed(1)}%`;

        // const raw = document.createElement("span");
        // raw.className = "score author-sim";
        // raw.textContent = `Raw Score: ${(rec.raw_score * 100).toFixed(1)}%`;

        const explanation = document.createElement("div");
        explanation.className = "score font-sm text-muted mt-1";
        explanation.textContent = rec.explanation;

        // Rozet (Badge)
        // const badge = document.createElement("span");
        // badge.className = "badge";
        // if (rec.source === "cf") {
        //     badge.classList.add("primary-badge");
        //     badge.textContent = "Collaborative";
        // } else {
        //     badge.classList.add("secondary-badge");
        //     badge.textContent = "Content-Based";
        // }

        // Yapıyı birleştir
        scoreContainer.appendChild(score);
        // scoreContainer.appendChild(raw);
        // scoreContainer.appendChild(badge);

        info.appendChild(title);
        info.appendChild(author);
        info.appendChild(scoreContainer);
        info.appendChild(explanation);

        card.appendChild(img);
        card.appendChild(info);

        container.appendChild(card);
    });
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