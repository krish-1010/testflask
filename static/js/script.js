async function sendOTP() {
    let email = document.getElementById("email").value;
    if (!email) {
        alert("Enter your email!");
        return;
    }

    let response = await fetch('/send-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email })
    });

    let result = await response.json();
    alert(result.message);

    if (result.success) {
        document.getElementById("email-step").style.display = "none";
        document.getElementById("otp-step").style.display = "block";
    }
}

async function verifyOTP() {
    let email = document.getElementById("email").value;
    let otp = document.getElementById("otp").value;

    let response = await fetch('/verify-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, otp: otp })
    });

    let result = await response.json();
    alert(result.message);

    if (result.success) {
        document.getElementById("otp-step").style.display = "none";
        document.getElementById("reset-step").style.display = "block";
    }
}

async function resetPassword() {
    let email = document.getElementById("email").value;
    let newPassword = document.getElementById("new-password").value;
    let confirmPassword = document.getElementById("confirm-password").value;

    if (newPassword !== confirmPassword) {
        alert("Passwords do not match!");
        return;
    }

    let response = await fetch('/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ otp: document.getElementById("otp").value, new_password: newPassword })  
    });

    let result = await response.json();
    alert(result.message);

    if (result.success) {
        window.location.href = "login.html";
    }
}
