document.addEventListener('DOMContentLoaded', function () {
    const loginBtn = document.getElementById('login-btn');
    const loginModal = document.getElementById('loginModal');
    const loginSubmitBtn = document.getElementById('login-submit-btn');
    const userIdInput = document.getElementById('user-id-modal-input'); 

    if (loginBtn && loginModal) {
        loginBtn.addEventListener('click', function () {
            const modal = new bootstrap.Modal(loginModal);
            modal.show();
        });
    }

    if (loginSubmitBtn && userIdInput) {
        loginSubmitBtn.addEventListener('click', function () {
            const userId = userIdInput.value.trim();

            if (!userId) {
                alert('Please enter a user ID!');
                return;
            }

            fetch(`/login/${userId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ userId: userId })  // backend'te kullanılmasa da sorun olmaz
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.href = `/login-handle/${userId}`;
                } else {
                    alert('Login failed!');
                }
            })
            .catch(error => {
                console.error('Login error:', error);
                alert('An error occurred during login.');
            });
        });
    }
});
