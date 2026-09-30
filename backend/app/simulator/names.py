"""Small hand-written name lists per nationality (no Faker, so results are fully reproducible)."""

# nationality -> (population weight, first names, last names)
NATIONALITIES: dict[str, tuple[int, list[str], list[str]]] = {
    "Indian": (24,
        ["Rajesh", "Suresh", "Anil", "Vijay", "Sanjay", "Manoj", "Deepak", "Ramesh", "Arun", "Prakash", "Mohan", "Kiran"],
        ["Kumar", "Sharma", "Singh", "Patel", "Nair", "Reddy", "Yadav", "Gupta", "Menon", "Pillai", "Verma", "Das"]),
    "Pakistani": (20,
        ["Imran", "Bilal", "Tariq", "Usman", "Faisal", "Nadeem", "Kamran", "Asif", "Zubair", "Shahid", "Adnan", "Rashid"],
        ["Khan", "Ahmed", "Ali", "Hussain", "Malik", "Butt", "Iqbal", "Shah", "Chaudhry", "Qureshi", "Raza", "Sheikh"]),
    "Filipino": (10,
        ["Jose", "Juan", "Mark", "Angelo", "Ramil", "Rodel", "Jerome", "Noel", "Arnel", "Romeo", "Ferdinand", "Carlo"],
        ["Santos", "Reyes", "Cruz", "Bautista", "Garcia", "Mendoza", "Torres", "Flores", "Ramos", "Aquino", "Castillo", "Villanueva"]),
    "Bangladeshi": (12,
        ["Rahim", "Karim", "Jamal", "Hasan", "Sohel", "Rubel", "Faruk", "Shamim", "Masud", "Alamgir", "Babul", "Habib"],
        ["Uddin", "Rahman", "Islam", "Hossain", "Miah", "Chowdhury", "Akter", "Sarkar", "Talukdar", "Mondal", "Bhuiyan", "Khatun"]),
    "Nepali": (8,
        ["Bishal", "Ramesh", "Suman", "Prem", "Dipak", "Krishna", "Bikash", "Sunil", "Rajan", "Nabin", "Hari", "Santosh"],
        ["Thapa", "Gurung", "Rai", "Tamang", "Shrestha", "Magar", "Karki", "Adhikari", "Limbu", "Bhandari", "Poudel", "Basnet"]),
    "Egyptian": (8,
        ["Mahmoud", "Ahmed", "Mostafa", "Khaled", "Hossam", "Tamer", "Ibrahim", "Sherif", "Amr", "Walid", "Ayman", "Essam"],
        ["Hassan", "Mohamed", "Ibrahim", "Youssef", "Saleh", "Abdelrahman", "Farouk", "Mansour", "Nasser", "Fathy", "Salem", "Gaber"]),
    "Sri Lankan": (6,
        ["Nuwan", "Chaminda", "Sampath", "Lasith", "Kasun", "Dilshan", "Ruwan", "Thushara", "Asanka", "Pradeep", "Janaka", "Lakmal"],
        ["Perera", "Fernando", "Silva", "Jayasuriya", "Bandara", "Wickramasinghe", "Rajapaksa", "Gunawardena", "Dissanayake", "Herath", "Weerasinghe", "Kumara"]),
    "Emirati": (4,
        ["Khalid", "Saeed", "Hamad", "Rashid", "Mansoor", "Sultan", "Abdullah", "Majid", "Salem", "Obaid", "Humaid", "Juma"],
        ["Al Mazrouei", "Al Nuaimi", "Al Shamsi", "Al Ketbi", "Al Falasi", "Al Suwaidi", "Al Dhaheri", "Al Marri", "Al Hamadi", "Al Mansoori", "Al Blooshi", "Al Ameri"]),
    "Other": (8,
        ["Daniel", "Michael", "Omar", "Yusuf", "Peter", "Samuel", "Hassan", "Joseph", "Tesfaye", "David", "Kofi", "Ali"],
        ["Mensah", "Tadesse", "Abdi", "Johnson", "Okafor", "Mwangi", "Haddad", "Nasser", "Smith", "Yilmaz", "Petrov", "Osei"]),
}

TRAINER_NAMES = [
    "Fatima Al Zaabi", "Mohammed Rizvi", "Sarah Thompson", "Ahmed Farouk", "Priya Menon",
    "Omar Haddad", "Linda Fernandes", "Yousef Al Hashemi", "Grace Okonkwo", "Ravi Shankar",
]

DEPOTS = ["Al Quoz Depot", "Jebel Ali Depot", "Al Qusais Depot", "Sharjah Road Depot"]
