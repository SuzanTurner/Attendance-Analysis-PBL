// show/hide password toggle
function togglePassword(){
   var passwordField = document.getElementById('password');
   if(passwordField.type === "password") {
        passwordField.type = "text";
   } else {
    passwordField.type = "password";
   }
}

// CGPA Calculation

function generateInputs() {
   let totalSubjects = document.getElementById('totalSubjects').value;
   let container = document.getElementById('subjects-container');
   container.innerHTML = "";

   for (let i = 1; i <= totalSubjects; i++) {
       container.innerHTML += `
           <div class="form-group">
               <label>Grade Points for Subject ${i}:</label>
               <input type="number" class="form-control grade-point" min="0" max="10" required>
               <label>Credits for Subject ${i}:</label>
               <input type="number" class="form-control credits" min="1" required>
           </div>
       `;
   }
}

function calculateCGPA() {
   let gradePoints = document.querySelectorAll('.grade-point');
   let credits = document.querySelectorAll('.credits');
   let totalCredits = 0, weightedSum = 0;

   for (let i = 0; i < gradePoints.length; i++) {
       let gp = parseFloat(gradePoints[i].value);
       let cr = parseFloat(credits[i].value);

       if (!isNaN(gp) && !isNaN(cr)) {
           weightedSum += gp * cr;
           totalCredits += cr;
       }
   }

   let cgpa = (weightedSum / totalCredits).toFixed(2);
   document.getElementById('cgpa-result').innerHTML = "Your CGPA is: " + (isNaN(cgpa) ? "Invalid Input" : cgpa);
}



