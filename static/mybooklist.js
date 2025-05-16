// Configuration
let currentPage = 1;
const booksPerPage = 10;
let totalBooks = 0;
let allBooks = [];

// DOM Elements
const userIdDisplay = document.getElementById('userIdDisplay');
const myBookListResults = document.getElementById('myBookListResults');
const prevPageBtn = document.getElementById('prevPage');
const nextPageBtn = document.getElementById('nextPage');
const pageInfo = document.getElementById('pageInfo');
const getRecommendationsBtn = document.getElementById('getRecommendationsBtn');
const recommendationResults = document.getElementById('recommendationResults');

// Navigation Buttons
document.getElementById('backBtn').addEventListener('click', () => window.location.href = '/');
document.getElementById('backToSearchBtn').addEventListener('click', () => {
    window.location.href = `/login-handle/${userIdDisplay.textContent}`;
});

// Load books on page load
document.addEventListener('DOMContentLoaded', () => loadBooks(userIdDisplay.textContent));

// Load books from API with pagination
async function loadBooks(userId) {
    try {
        const res = await fetch(`/api/user/${userId}/books?page=${currentPage}`);
        const data = await res.json();

        if (data.success) {
            allBooks = data.books;
            totalBooks = data.total;
            updatePagination();
            displayBooks();
        } else {
            showNoBooksMessage(data.message || 'Failed to load books');
        }
    } catch (error) {
        console.error('Error loading books:', error);
        showNoBooksMessage('Error loading books');
    }
}

// Display books in 2 rows with max 5 books each
function displayBooks() {
    myBookListResults.innerHTML = '';
    if (allBooks.length === 0) {
        showNoBooksMessage('You have no books in your list yet');
        return;
    }

    const row1 = document.createElement('div');
    row1.className = 'book-row';
    const row2 = document.createElement('div');
    row2.className = 'book-row';

    allBooks.slice(0, 5).forEach(book => row1.appendChild(createBookCard(book)));
    allBooks.slice(5, 10).forEach(book => row2.appendChild(createBookCard(book)));

    myBookListResults.appendChild(row1);
    myBookListResults.appendChild(row2);
}

// Create book card element
function createBookCard(book) {
    const card = document.createElement('div');
    card.className = 'book-card';
    card.innerHTML = `
        <img src="${book.image || 'https://via.placeholder.com/150x200?text=No+Cover'}" 
             alt="${book.title || 'Untitled'}"
             onerror="this.src='https://via.placeholder.com/150x200?text=No+Cover'">
        <div class="book-info">
            <h3>${book.title || 'Untitled'}</h3>
            <p class="book-author">${book.author || 'Unknown author'}</p>
            <p class="book-rating">⭐ ${book.rating || 'N/A'}/10</p>
            <p class="book-isbn">ISBN: ${book.isbn || 'N/A'}</p>
        </div>`;
    return card;
}

// Update pagination UI
function updatePagination() {
    const totalPages = Math.ceil(totalBooks / booksPerPage);
    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
    prevPageBtn.disabled = currentPage <= 1;
    nextPageBtn.disabled = currentPage >= totalPages;
    document.getElementById('paginationControls').style.display = totalPages > 1 ? 'flex' : 'none';
}

// Pagination buttons
prevPageBtn.addEventListener('click', () => {
    if (currentPage > 1) {
        currentPage--;
        loadBooks(userIdDisplay.textContent);
    }
});
nextPageBtn.addEventListener('click', () => {
    const totalPages = Math.ceil(totalBooks / booksPerPage);
    if (currentPage < totalPages) {
        currentPage++;
        loadBooks(userIdDisplay.textContent);
    }
});

// Show message if no books
function showNoBooksMessage(message) {
    myBookListResults.innerHTML = `
        <div class="no-books-message">
            <p>${message}</p>
            <button onclick="window.location.href='/login-handle/${userIdDisplay.textContent}'">Search Books to Add</button>
        </div>`;
    document.getElementById('paginationControls').style.display = 'none';
}

// Recommendations button
getRecommendationsBtn.addEventListener('click', async () => {
    const userId = userIdDisplay.textContent;
    getRecommendationsBtn.disabled = true;
    getRecommendationsBtn.textContent = 'Loading...';

    try {
        const res = await fetch(`/api/user/${userId}/recommend`);
        const data = await res.json();

        recommendationResults.innerHTML = '';

        if (!data.success || !data.recommendations?.length) {
            recommendationResults.innerHTML = `<p class="no-recommendations">No recommendations found. Try adding more books to your library.</p>`;
            return;
        }

        data.recommendations.forEach(rec => {
            const card = document.createElement('div');
            card.className = 'recommendation-card';
            card.innerHTML = `
                <img src="${rec.image || 'https://via.placeholder.com/150x200?text=No+Cover'}" alt="${rec.title || 'Untitled'}">
                <div class="recommendation-info">
                    <h3>${rec.title || 'Untitled'}</h3>
                    <p>${rec.author || 'Unknown author'}</p>
                    ${rec.similarity ? `<div class="similarity-badge">Similarity: ${rec.similarity.toFixed(2)}</div>` : ''}
                    ${rec.predicted_rating ? `<div class="predicted-rating">Predicted rating: ${rec.predicted_rating.toFixed(1)}/10</div>` : ''}
                </div>`;
            recommendationResults.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading recommendations:', error);
        recommendationResults.innerHTML = `<p class="error-message">Error loading recommendations. Please try again.</p>`;
    } finally {
        getRecommendationsBtn.disabled = false;
        getRecommendationsBtn.textContent = 'Get Recommendations';
    }
});
