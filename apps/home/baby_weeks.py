"""Weekly "baby this week" notes for the mother's dashboard.

General, widely shared information about typical development. Sizes are
rough comparisons, and every pregnancy is different.
"""

# week: (size comparison, what is happening with the baby, a tip for the mother)
WEEKS = {
    4: ("a poppy seed", "The fertilised egg has settled into the lining of your womb, and the placenta is starting to form.",
        "If you haven't yet, ask your doctor about a daily folic acid supplement and book your first check-up."),
    5: ("a sesame seed", "The heart and the neural tube, which becomes the brain and spinal cord, are beginning to form.",
        "Avoid alcohol and smoking, and check with your doctor before taking any medicine."),
    6: ("a lentil", "Small buds that will become arms and legs are appearing, and a heartbeat may be seen on an early scan.",
        "Small, frequent meals and plain snacks can help if you feel sick."),
    7: ("a blueberry", "The brain is growing quickly, and the arms and legs are getting longer.",
        "Tiredness is very common now. Rest when you can."),
    8: ("a raspberry", "Fingers and toes are starting to form, and your baby is making tiny movements you can't feel yet.",
        "Keep a bottle of water nearby and sip through the day."),
    9: ("a grape", "The main organs have begun to form and will keep developing in the months ahead.",
        "Ask your doctor which tests and scans are planned for the coming weeks."),
    10: ("a strawberry", "Tiny nails are starting to grow, and the elbows and knees can bend.",
         "Add iron-rich foods such as leafy greens, beans and lean meat to your meals."),
    11: ("a fig", "The bones are beginning to harden, and the head makes up about half of your baby's length.",
         "Gentle activity such as walking is good for most pregnancies. Check with your doctor first."),
    12: ("a lime", "Reflexes are developing: your baby can open and close their fingers and curl their toes.",
         "Nausea often starts to ease around now. Tell your doctor if it doesn't."),
    13: ("a lemon", "Your baby's own fingerprints are forming. This is the last week of the first trimester.",
         "Many people share their news around now. Do it whenever it feels right for you."),
    14: ("a peach", "Your baby can now make facial expressions such as squinting and frowning.",
         "Energy often returns in the second trimester. It's a good time to build a gentle routine."),
    15: ("an apple", "The bones keep getting stronger, and your baby can sense light through closed eyelids.",
         "Keep up regular meals with protein, fruit and vegetables."),
    16: ("an avocado", "The ears are close to their final position, and your baby may soon begin to hear sounds.",
         "Talk or sing to your baby if you like. Many parents enjoy starting now."),
    17: ("a pear", "Your baby is beginning to store fat, which will help keep them warm after birth.",
         "A pillow between your knees can make sleeping on your side more comfortable."),
    18: ("a bell pepper", "You may begin to feel the first light flutters. For some this comes a few weeks later, which is normal.",
         "Note when you first feel movement and mention it at your next visit."),
    19: ("a mango", "A creamy coating called vernix is forming to protect your baby's skin.",
         "Stretch gently and change position often if your back aches."),
    20: ("a banana", "You are halfway there. A detailed scan of your baby is commonly done around now.",
         "Write down questions for your scan appointment so you don't forget them."),
    21: ("a carrot", "Movements are getting stronger, and your baby is swallowing small amounts of amniotic fluid.",
         "Calcium-rich foods such as milk, yoghurt and small fish with bones support your baby's bones."),
    22: ("a small papaya", "Eyebrows and eyelids are formed, and your baby's sense of touch is developing.",
         "Mild swelling of the feet is common. Put your feet up when you can."),
    23: ("a grapefruit", "Hearing is improving, and your baby may respond to loud sounds or your voice.",
         "Keep logging your weight and blood pressure so your doctor can see the trend."),
    24: ("an ear of corn", "The lungs are developing the tiny branches they will need for breathing.",
         "A blood sugar test is commonly offered between 24 and 28 weeks. Ask your doctor about it."),
    25: ("a cauliflower", "Hair is growing, and your baby is getting to know the sound of your voice.",
         "Short walks after meals can help with digestion and energy."),
    26: ("a head of lettuce", "Your baby's eyes are beginning to open, and they have regular times of sleep and activity.",
         "Notice when your baby is usually active. It will help when you start counting kicks."),
    27: ("a head of broccoli", "The brain is very active now. This is the last week of the second trimester.",
         "Ask your doctor how often your visits will be in the third trimester."),
    28: ("an eggplant", "Welcome to the third trimester. Your baby can blink and is putting on weight steadily.",
         "This is a good time to start daily kick counts. Use the Kicks page to record them."),
    29: ("a butternut squash", "The bones are fully formed but still soft, and kicks may feel stronger.",
         "If your baby moves much less than usual, contact your doctor straight away."),
    30: ("a cabbage", "The brain is developing quickly, and your baby can tell light from dark.",
         "Rest on your side when you lie down, and get up slowly to avoid feeling dizzy."),
    31: ("a coconut", "Your baby can turn their head from side to side and is gaining weight quickly.",
         "You may feel practice tightenings. Tell your doctor if they become regular or painful."),
    32: ("a pomelo", "Your baby is practising breathing movements and may be settling into a head-down position.",
         "Talk with your doctor about your birth plan and where you will deliver."),
    33: ("a pineapple", "The bones are hardening, though the skull stays soft and flexible for birth.",
         "Eat smaller meals more often if you get heartburn or feel full quickly."),
    34: ("a cantaloupe", "The lungs and nervous system are continuing to mature.",
         "Prepare your hospital bag and keep your records and ID together."),
    35: ("a honeydew melon", "Your baby has less room now, so movements may feel more like rolls and stretches.",
         "Movements may feel different, but they should not become fewer. Keep counting."),
    36: ("a large papaya", "Your baby may move lower into your pelvis, getting ready for birth.",
         "Know the way to your hospital and who will go with you."),
    37: ("a winter melon", "Your baby is considered early term and is practising sucking and swallowing.",
         "Learn the signs of labour: regular contractions that get stronger, or your waters breaking."),
    38: ("a small pumpkin", "Your baby has a firm grasp, and the organs are ready for life outside the womb.",
         "Rest as much as you can, and keep your phone charged and nearby."),
    39: ("a small watermelon", "Your baby is full term. The brain and lungs keep maturing right up to birth.",
         "Call your doctor or hospital when contractions become regular, or sooner if you are worried."),
    40: ("a watermelon", "This is your due date week. Only a small share of babies arrive exactly on the day.",
         "Keep counting kicks, and contact your doctor if you have any concerns while you wait."),
}

EARLY = ("smaller than a poppy seed", "These are the very first days. Your body is preparing, and pregnancy is counted from the first day of your last period.",
         "Eat well, rest, and ask your doctor about starting folic acid.")
LATE = ("a watermelon", "You are past your due date, which is common. Your baby is ready to meet you.",
        "Your doctor will check on you both more often now and talk through the next steps with you.")


def baby_this_week(weeks):
    """Returns {'week', 'size', 'baby', 'tip'} for a week of pregnancy."""
    if weeks < 4:
        size, baby, tip = EARLY
    elif weeks > 40:
        size, baby, tip = LATE
    else:
        size, baby, tip = WEEKS[weeks]
    return {'week': weeks, 'size': size, 'baby': baby, 'tip': tip}